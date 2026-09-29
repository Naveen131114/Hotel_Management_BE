from datetime import datetime

from flask import Blueprint, request

from src import db
from src.models.users import User
from src.models.businesses import Business
from src.models.branches import Branch
from src.services import subscription_service
from src.utils import (
    success_response, error_response, encode_token, auth_required, get_current_user, log_activity,
)
from src.utils.constants import (
    ACTIVITY_LOGIN, PERMISSION_ACTIONS, PERMISSION_FULL, ROLE_GUEST, ROLE_OWNER,
    ROLE_STAFF, ROLE_SUPER_ADMIN,
)

bp = Blueprint('auth', __name__, url_prefix='/api/auth')


def auth_payload(user):
    """Panel login payload: user + business + branches + permissions + subscription"""
    business = db.session.get(Business, user.business_id) if user.business_id else None
    if user.role == ROLE_SUPER_ADMIN:
        branches = Branch.query.order_by(Branch.name.asc()).all()
    elif user.role == ROLE_STAFF:
        branches = user.allowed_branches
    elif business is not None:
        branches = Branch.query.filter_by(business_id=business.id).order_by(Branch.name.asc()).all()
    else:
        branches = []

    payload = user.to_dict()
    payload.update({
        'role': user.role,
        'permissions': list(PERMISSION_ACTIONS.get(
            user.permission_level or PERMISSION_FULL, PERMISSION_ACTIONS[PERMISSION_FULL]
        )),
        'business': business.to_dict() if business else None,
        'allowed_branches': [branch.to_dict() for branch in branches],
        'subscription': subscription_service.limit_status(user.business_id) if user.business_id else None,
        'is_panel_user': user.role != ROLE_GUEST
    })
    return payload


@bp.route('/register', methods=['POST'])
def register():
    """Register a guest account (public website guests keep working as before)"""
    try:
        data = request.get_json()

        # Validate required fields
        required_fields = ['first_name', 'last_name', 'email', 'password']
        if not all(field in data for field in required_fields):
            return error_response('Missing required fields', 400)

        # Check if user already exists
        if User.query.filter_by(email=data['email']).first():
            return error_response('User already exists', 400)

        business_id = None
        if data.get('business_slug'):
            business = Business.query.filter_by(slug=str(data['business_slug']).lower()).first()
            if business is None:
                return error_response('Hotel not found', 404)
            business_id = business.id

        # Create new user
        user = User(
            first_name=data['first_name'],
            last_name=data['last_name'],
            email=data['email'],
            phone=data.get('phone'),
            id_number=data.get('id_number'),
            id_type=data.get('id_type'),
            nationality=data.get('nationality'),
            address=data.get('address'),
            business_id=business_id,
            role=ROLE_GUEST
        )
        user.set_password(data['password'])

        db.session.add(user)
        db.session.commit()

        # Generate token
        token = encode_token(user.id)

        return success_response('User registered successfully', user.to_dict(), token, 201)

    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/login', methods=['POST'])
def login():
    """Login for super admin, hotel owner, staff (and guests of the public site)"""
    try:
        data = request.get_json()

        if not data.get('email') or not data.get('password'):
            return error_response('Email and password required', 400)

        user = User.query.filter_by(email=data['email']).first()
        if not user or not user.password_hash or not user.check_password(data['password']):
            return error_response('Invalid email or password', 401)

        if not user.is_active:
            return error_response('Your account is inactive. Please contact your administrator.', 403)

        if user.business_id and user.role in (ROLE_OWNER, ROLE_STAFF):
            business = db.session.get(Business, user.business_id)
            if business is not None and not business.is_active:
                return error_response('Your hotel account has been deactivated. Please contact support.', 403)

        user.last_login_at = datetime.utcnow()
        db.session.commit()

        token = encode_token(user.id)
        log_activity(ACTIVITY_LOGIN, 'auth', user.id, user.email,
                     f"{user.first_name} logged in as {user.role}", user=user,
                     business_id=user.business_id, branch_id=user.branch_id)
        return success_response('Login successful', auth_payload(user), token, 200)

    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/me', methods=['GET'])
@auth_required()
def me():
    """Refresh the current user, branches, permissions and subscription state"""
    try:
        payload = auth_payload(get_current_user())
        payload['selected_branch_id'] = request.headers.get('X-Branch-Id')
        return success_response('Current user fetched successfully', payload, status_code=200)
    except Exception as e:
        return error_response(f'Error: {str(e)}', 500)
