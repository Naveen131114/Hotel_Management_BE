from flask import Blueprint, request

from src import db
from src.models.users import User
from src.models.branches import Branch
from src.models.staff_branches import StaffBranch
from src.services import subscription_service
from src.utils import (
    success_response, error_response, auth_required, require_permission,
    log_activity, get_current_user, current_business_id,
)
from src.utils.constants import (
    ACTIVITY_CREATE, ACTIVITY_DELETE, ACTIVITY_UPDATE, MODULE_STAFF,
    PERMISSION_LEVELS, PERMISSION_FULL, ROLE_OWNER, ROLE_STAFF,
)

bp = Blueprint('staff', __name__, url_prefix='/api/staff')


def _staff_query():
    return User.query.filter_by(business_id=current_business_id(), role=ROLE_STAFF)


def _validate_branch_ids(business_id, branch_ids):
    """Return (valid_ids, error) - branches must belong to the same hotel"""
    if not branch_ids:
        return [], None
    ids = []
    for value in branch_ids:
        if str(value).isdigit():
            ids.append(int(value))
    if not ids:
        return [], None
    found = Branch.query.filter(Branch.business_id == business_id, Branch.id.in_(ids)).all()
    if len(found) != len(set(ids)):
        return None, 'One or more branches do not belong to your hotel'
    return [branch.id for branch in found], None


def _set_branches(staff_user, branch_ids):
    StaffBranch.query.filter_by(user_id=staff_user.id).delete()
    for branch_id in branch_ids:
        db.session.add(StaffBranch(user_id=staff_user.id, branch_id=branch_id))


@bp.route('', methods=['GET'])
@auth_required(ROLE_OWNER)
@require_permission('view')
def get_all_staff():
    """List the staff logins of the current hotel"""
    try:
        status = request.args.get('status')
        query = _staff_query()
        if status == 'active':
            query = query.filter(User.is_active.is_(True))
        elif status == 'inactive':
            query = query.filter(User.is_active.is_(False))
        staff = query.order_by(User.first_name.asc()).all()
        return success_response('Staff fetched successfully',
                                [member.to_dict() for member in staff], status_code=200)
    except Exception as e:
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['GET'])
@auth_required(ROLE_OWNER)
@require_permission('view')
def get_staff(id):
    """Get a single staff member"""
    try:
        member = _staff_query().filter(User.id == id).first()
        if not member:
            return error_response('Staff member not found', 404)
        return success_response('Staff fetched successfully', member.to_dict(), status_code=200)
    except Exception as e:
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/permissions', methods=['GET'])
@auth_required()
def list_permission_levels():
    """Available permission levels (used by the staff form)"""
    return success_response('Permission levels fetched successfully', {
        'levels': [
            {'value': 'view_only', 'label': 'View Only', 'allows': ['view']},
            {'value': 'edit', 'label': 'Edit Only', 'allows': ['view', 'create', 'edit']},
            {'value': 'full', 'label': 'Full Access', 'allows': ['view', 'create', 'edit', 'delete']}
        ]
    })


@bp.route('/<int:id>/branches', methods=['PUT'])
@auth_required(ROLE_OWNER)
@require_permission('edit')
def assign_staff_branches(id):
    """Assign one or more branches to a staff member"""
    try:
        member = _staff_query().filter(User.id == id).first()
        if not member:
            return error_response('Staff member not found', 404)

        data = request.get_json() or {}
        branch_ids, error = _validate_branch_ids(current_business_id(), data.get('branch_ids', []))
        if error:
            return error_response(error, 400)

        _set_branches(member, branch_ids)
        db.session.commit()

        log_activity(ACTIVITY_UPDATE, MODULE_STAFF, member.id, member.email,
                     f"Updated branch access for {member.first_name} {member.last_name}")
        return success_response('Branches assigned successfully', member.to_dict(), status_code=200)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)


@bp.route('', methods=['POST'])
@auth_required(ROLE_OWNER)
@require_permission('create')
def create_staff():
    """Create a staff login - the subscription staff limit is enforced here"""
    try:
        data = request.get_json() or {}
        required = ['first_name', 'email', 'password']
        if not all(data.get(field) for field in required):
            return error_response('First name, email and password are required', 400)
        if len(str(data.get('password'))) < 6:
            return error_response('Password must be at least 6 characters', 400)

        business_id = current_business_id()
        allowed, message, usage, limits = subscription_service.check_limit(business_id, 'staff')
        if not allowed:
            return error_response(message, 403)

        if User.query.filter_by(email=data['email']).first():
            return error_response('This email is already registered', 400)

        permission_level = data.get('permission_level', PERMISSION_FULL)
        if permission_level not in PERMISSION_LEVELS:
            return error_response('Invalid permission level', 400)

        branch_ids, error = _validate_branch_ids(business_id, data.get('branch_ids', []))
        if error:
            return error_response(error, 400)

        actor = get_current_user()
        member = User(
            first_name=data['first_name'],
            last_name=data.get('last_name', ''),
            email=data['email'],
            phone=data.get('phone'),
            business_id=business_id,
            branch_id=branch_ids[0] if branch_ids else None,
            role=ROLE_STAFF,
            permission_level=permission_level,
            designation=data.get('designation'),
            is_active=data.get('is_active', True),
            created_by=actor.id if actor else None
        )
        member.set_password(data['password'])
        db.session.add(member)
        db.session.flush()
        _set_branches(member, branch_ids)
        db.session.commit()

        log_activity(ACTIVITY_CREATE, MODULE_STAFF, member.id, member.email,
                     f"Created staff login for {member.first_name} {member.last_name}")
        payload = member.to_dict()
        payload['subscription_usage'] = {**usage, 'staff_limit': limits.get('max_staff')}
        return success_response('Staff created successfully', payload, status_code=201)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['PUT'])
@auth_required(ROLE_OWNER)
@require_permission('edit')
def update_staff(id):
    """Update a staff member, their permission level, branches and status"""
    try:
        member = _staff_query().filter(User.id == id).first()
        if not member:
            return error_response('Staff member not found', 404)

        data = request.get_json() or {}
        if data.get('email'):
            existing = User.query.filter_by(email=data['email']).first()
            if existing and existing.id != member.id:
                return error_response('This email is already registered', 400)
            member.email = data['email']

        for field in ('first_name', 'last_name', 'phone', 'designation'):
            if field in data:
                setattr(member, field, data[field])
        if 'is_active' in data:
            member.is_active = bool(data['is_active'])
        if data.get('permission_level'):
            if data['permission_level'] not in PERMISSION_LEVELS:
                return error_response('Invalid permission level', 400)
            member.permission_level = data['permission_level']
        if data.get('password'):
            if len(str(data['password'])) < 6:
                return error_response('Password must be at least 6 characters', 400)
            member.set_password(data['password'])

        if 'branch_ids' in data:
            branch_ids, error = _validate_branch_ids(current_business_id(), data.get('branch_ids') or [])
            if error:
                return error_response(error, 400)
            _set_branches(member, branch_ids)
            member.branch_id = branch_ids[0] if branch_ids else None

        member.updated_by = get_current_user().id
        db.session.commit()

        log_activity(ACTIVITY_UPDATE, MODULE_STAFF, member.id, member.email,
                     f"Updated staff {member.first_name} {member.last_name}")
        return success_response('Staff updated successfully', member.to_dict(), status_code=200)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['DELETE'])
@auth_required(ROLE_OWNER)
@require_permission('delete')
def delete_staff(id):
    """Deactivate a staff login (kept for audit history, login access revoked)"""
    try:
        member = _staff_query().filter(User.id == id).first()
        if not member:
            return error_response('Staff member not found', 404)

        member.is_active = False
        StaffBranch.query.filter_by(user_id=member.id).delete()
        db.session.commit()

        log_activity(ACTIVITY_DELETE, MODULE_STAFF, member.id, member.email,
                     f"Deactivated staff {member.first_name} {member.last_name}")
        return success_response('Staff deactivated successfully', member.to_dict(), status_code=200)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)

