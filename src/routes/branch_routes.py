from flask import Blueprint, request

from src import db
from src.models.branches import Branch
from src.models.rooms import Room
from src.models.room_records import RoomRecord
from src.models.staff_branches import StaffBranch
from src.services import subscription_service
from src.utils import (
    success_response, error_response, auth_required, require_permission,
    log_activity, get_current_user, allowed_branch_ids, current_business_id,
)
from src.utils.constants import (
    ACTIVITY_CREATE, ACTIVITY_DELETE, ACTIVITY_UPDATE, MODULE_BRANCHES,
    ROLE_OWNER, ROLE_STAFF, ROLE_SUPER_ADMIN,
)

bp = Blueprint('branches', __name__, url_prefix='/api/branches')


def _scoped_query():
    """Branches visible to the current user (tenant + branch access aware)"""
    user = get_current_user()
    query = Branch.query
    if user.role == ROLE_SUPER_ADMIN:
        scoped = request.args.get('business_id')
        if scoped and str(scoped).isdigit():
            query = query.filter(Branch.business_id == int(scoped))
        return query
    query = query.filter(Branch.business_id == user.business_id)
    allowed = allowed_branch_ids()
    if allowed is not None:
        query = query.filter(Branch.id.in_(allowed)) if allowed else query.filter(db.text('1 = 0'))
    return query


@bp.route('', methods=['GET'])
@auth_required()
@require_permission('view')
def get_all_branches():
    """List branches of the current hotel (staff only see their branches)"""
    try:
        query = _scoped_query()
        if request.args.get('active_only') in ('1', 'true', 'True'):
            query = query.filter(Branch.is_active.is_(True))
        branches = query.order_by(Branch.name.asc()).all()
        return success_response('Branches fetched successfully',
                                [b.to_dict() for b in branches], status_code=200)
    except Exception as e:
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['GET'])
@auth_required()
@require_permission('view')
def get_branch(id):
    """Get a single branch"""
    try:
        branch = _scoped_query().filter(Branch.id == id).first()
        if not branch:
            return error_response('Branch not found', 404)
        return success_response('Branch fetched successfully', branch.to_dict(), status_code=200)
    except Exception as e:
        return error_response(f'Error: {str(e)}', 500)


@bp.route('', methods=['POST'])
@auth_required(ROLE_OWNER)
@require_permission('create')
def create_branch():
    """Create a branch (validated against the subscription branch limit)"""
    try:
        data = request.get_json() or {}
        if not data.get('name'):
            return error_response('Branch name is required', 400)

        business_id = current_business_id()
        allowed, message, _usage, _limits = subscription_service.check_limit(business_id, 'branch')
        if not allowed:
            return error_response(message, 403)

        if Branch.query.filter_by(business_id=business_id, name=data['name']).first():
            return error_response('A branch with this name already exists', 400)

        user = get_current_user()
        branch = Branch(
            business_id=business_id,
            name=data['name'],
            code=data.get('code'),
            address=data.get('address'),
            city=data.get('city'),
            phone=data.get('phone'),
            email=data.get('email'),
            gst_number=data.get('gst_number'),
            is_active=data.get('is_active', True),
            created_by=user.id if user else None
        )
        db.session.add(branch)
        db.session.commit()

        log_activity(ACTIVITY_CREATE, MODULE_BRANCHES, branch.id, branch.name,
                     f"Created branch {branch.name}", branch_id=branch.id)
        return success_response('Branch created successfully', branch.to_dict(), status_code=201)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['PUT'])
@auth_required(ROLE_OWNER)
@require_permission('edit')
def update_branch(id):
    """Update a branch of the current hotel"""
    try:
        branch = Branch.query.filter_by(id=id, business_id=current_business_id()).first()
        if not branch:
            return error_response('Branch not found', 404)

        data = request.get_json() or {}
        for field in ('name', 'code', 'address', 'city', 'phone', 'email', 'gst_number', 'is_active'):
            if field in data:
                setattr(branch, field, data[field])
        user = get_current_user()
        branch.updated_by = user.id if user else None
        db.session.commit()

        log_activity(ACTIVITY_UPDATE, MODULE_BRANCHES, branch.id, branch.name,
                     f"Updated branch {branch.name}", branch_id=branch.id)
        return success_response('Branch updated successfully', branch.to_dict(), status_code=200)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['DELETE'])
@auth_required(ROLE_OWNER)
@require_permission('delete')
def delete_branch(id):
    """Delete a branch (blocked while rooms/bookings exist so data is never lost)"""
    try:
        branch = Branch.query.filter_by(id=id, business_id=current_business_id()).first()
        if not branch:
            return error_response('Branch not found', 404)

        rooms = Room.query.filter_by(branch_id=branch.id).count()
        bookings = RoomRecord.query.filter_by(branch_id=branch.id).count()
        if rooms or bookings:
            return error_response(
                f'This branch has {rooms} room(s) and {bookings} booking(s). '
                'Move or delete them first, or deactivate the branch instead.', 400
            )

        if Branch.query.filter_by(business_id=branch.business_id).count() <= 1:
            return error_response('At least one branch must exist for the hotel', 400)

        StaffBranch.query.filter_by(branch_id=branch.id).delete()
        name = branch.name
        db.session.delete(branch)
        db.session.commit()

        log_activity(ACTIVITY_DELETE, MODULE_BRANCHES, id, name, f"Deleted branch {name}")
        return success_response('Branch deleted successfully', status_code=200)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)

        return success_response('Branch fetched successfully', branch.to_dict(), status_code=200)
    except Exception as e:
        return error_response(f'Error: {str(e)}', 500)
