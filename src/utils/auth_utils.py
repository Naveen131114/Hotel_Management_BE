"""Authentication / authorization helpers for the multi-tenant SaaS.

Every protected endpoint goes through:
    token  ->  active user  ->  role  ->  business/tenant  ->  branch access
           ->  permission level  ->  subscription state  ->  requested resource
"""
from functools import wraps

from flask import request

from src import db
from src.models.users import User
from src.models.activity_logs import ActivityLog
from src.utils.jwt_utils import decode_token
from src.utils.response_handler import error_response
from src.utils.constants import (
    PERMISSION_ACTIONS, PERMISSION_FULL,
    ROLE_SUPER_ADMIN, ROLE_OWNER, ROLE_STAFF,
)

SAFE_METHODS = ('GET', 'HEAD', 'OPTIONS')


# ── Request context helpers ──────────────────────────────────────────────
def _user_id_from_header():
    """Read the JWT from the Authorization header and return the user id"""
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return None
    try:
        token = auth_header.split(' ')[1]
    except IndexError:
        return None
    return decode_token(token)


def requested_branch_id():
    """Branch chosen in the top navbar (X-Branch-Id header) or ?branch_id="""
    header_value = request.headers.get('X-Branch-Id')
    if header_value and str(header_value).isdigit():
        return int(header_value)
    arg_value = request.args.get('branch_id')
    if arg_value and str(arg_value).isdigit():
        return int(arg_value)
    return None


def get_current_user():
    """Return the authenticated user for the current request (or None)"""
    user = getattr(request, 'current_user', None)
    if user is not None:
        return user
    user_id = getattr(request, 'user_id', None) or _user_id_from_header()
    if not user_id:
        return None
    return db.session.get(User, user_id)


def current_business_id():
    """Tenant id of the current request (None for the super admin)"""
    return getattr(request, 'business_id', None)


def current_branch_id():
    """Active branch of the current request (None = all allowed branches)"""
    return getattr(request, 'branch_id', None)


def allowed_branch_ids():
    """Branch ids the current user may touch (None = all branches of the tenant)"""
    return getattr(request, 'allowed_branch_ids', None)


# ── Decorators ───────────────────────────────────────────────────────────
def auth_required(*roles, allow_inactive=False):
    """Protect an endpoint: valid token + active user + role + subscription state

    Sets on `request`: current_user, business_id, branch_id, allowed_branch_ids.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            user = get_current_user()
            if user is None:
                return error_response('Token is invalid, expired or user not found', 401)

            if not user.is_active and not allow_inactive:
                return error_response('Your account is inactive. Please contact your administrator.', 403)

            if roles and user.role not in roles:
                return error_response('You do not have access to this resource', 403)

            request.current_user = user
            request.business_id = user.business_id
            request.allowed_branch_ids = None
            request.branch_id = None

            selected_branch = requested_branch_id()

            if user.role == ROLE_STAFF and not user.is_guest():
                allowed = user.allowed_branch_ids()
                if selected_branch is not None and selected_branch not in allowed:
                    return error_response('You do not have access to the selected branch', 403)
                request.allowed_branch_ids = allowed
                request.branch_id = selected_branch if selected_branch in allowed else None
            else:
                request.branch_id = selected_branch

            # Subscription policy: expired subscription keeps read access but
            # blocks create/update/delete, so customer data is never lost.
            if user.role in (ROLE_OWNER, ROLE_STAFF) and request.method not in SAFE_METHODS:
                from src.services import subscription_service
                blocked = subscription_service.write_blocked_reason(user.business_id)
                if blocked:
                    return error_response(blocked, 403)

            return func(*args, **kwargs)
        return wrapper
    return decorator


def require_permission(action):
    """Enforce the staff permission level (view / create / edit / delete)"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            user = get_current_user()
            if user is None:
                return error_response('Unauthorized', 401)
            if not _can(user, action):
                return error_response(f'Your permission level does not allow you to {action} this record', 403)
            return func(*args, **kwargs)
        return wrapper
    return decorator


def _can(user, action):
    if user.role in (ROLE_SUPER_ADMIN, ROLE_OWNER):
        return True
    level = user.permission_level or PERMISSION_FULL
    return action in PERMISSION_ACTIONS.get(level, PERMISSION_ACTIONS[PERMISSION_FULL])



def can(action):
    """Permission check for the current user"""
    user = get_current_user()
    return bool(user and _can(user, action))


def assert_branch_access(branch_id):
    """Return an error tuple when the current user may not touch `branch_id`"""
    if branch_id is None:
        return error_response('branch_id is required', 400)
    user = get_current_user()
    if user is None:
        return error_response('Unauthorized', 401)
    if user.role == ROLE_SUPER_ADMIN:
        return None
    allowed = allowed_branch_ids()
    if allowed is not None and int(branch_id) not in allowed:
        return error_response('You do not have access to this branch', 403)
    return None


def tenant_scope(model, query=None, branch_id=None, respect_selection=True):
    """Apply tenant + branch isolation to a query on `model`.

    * super admin - unrestricted (all tenants), optionally filtered by ?business_id
    * owner       - own business, optionally narrowed to the selected branch
    * staff       - own business, only the branches assigned to the staff member
                    (or the single branch selected in the navbar)
    """
    query = query if query is not None else getattr(model, 'query')
    user = get_current_user()
    if user is None:
        return query.filter(db.text('1 = 0'))

    if user.role == ROLE_SUPER_ADMIN:
        scoped_business = request.args.get('business_id')
        if scoped_business and str(scoped_business).isdigit() and hasattr(model, 'business_id'):
            query = query.filter(model.business_id == int(scoped_business))
        return query

    if hasattr(model, 'business_id'):
        query = query.filter(model.business_id == user.business_id)

    if not hasattr(model, 'branch_id'):
        return query

    if branch_id is None and respect_selection:
        branch_id = current_branch_id()

    if branch_id is not None:
        return query.filter(model.branch_id == int(branch_id))

    allowed = allowed_branch_ids()
    if allowed is not None:
        if not allowed:
            return query.filter(db.text('1 = 0'))
        return query.filter(model.branch_id.in_(allowed))

    return query


def resolve_branch_id(payload_branch_id=None):
    """Decide which branch a newly created record belongs to (validated)"""
    user = get_current_user()
    branch_id = payload_branch_id or current_branch_id()
    allowed = allowed_branch_ids()
    if allowed is not None and branch_id is not None and int(branch_id) not in allowed:
        return None, error_response('You do not have access to this branch', 403)
    if branch_id is None and allowed:
        branch_id = allowed[0]
    return branch_id, None


def log_activity(action, module, record_id=None, record_ref=None, description=None,
                 user=None, business_id=None, branch_id=None):
    """Write an audit-log entry. Never breaks the calling operation."""
    try:
        user = user or get_current_user()
        entry = ActivityLog(
            business_id=business_id if business_id is not None else (user.business_id if user else None),
            branch_id=branch_id if branch_id is not None else current_branch_id(),
            user_id=user.id if user else None,
            user_name=(f"{user.first_name or ''} {user.last_name or ''}".strip() if user else 'System'),
            action=action,
            module=module,
            record_id=record_id,
            record_ref=record_ref,
            description=description
        )
        db.session.add(entry)
        db.session.commit()
    except Exception:
        db.session.rollback()
