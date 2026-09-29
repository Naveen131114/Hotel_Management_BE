from flask import Blueprint, request

from src import db
from src.models.users import User
from src.models.room_records import RoomRecord
from src.utils import (
    success_response, error_response, auth_required, require_permission, tenant_scope,
    log_activity, get_current_user, current_business_id,
)
from src.utils.constants import ACTIVITY_DELETE, ACTIVITY_UPDATE, MODULE_BOOKINGS, ROLE_GUEST

bp = Blueprint('users', __name__, url_prefix='/api/users')


def _guest_query():
    """Guest accounts of the current hotel (staff logins are managed under /api/staff)"""
    return tenant_scope(User, User.query.filter(User.role == ROLE_GUEST))


@bp.route('', methods=['GET'])
@auth_required()
@require_permission('view')
def get_all_users():
    """Get guests of the current hotel"""
    try:
        query = _guest_query()
        if request.args.get('search'):
            term = f"%{request.args.get('search')}%"
            query = query.filter(db.or_(
                User.first_name.ilike(term), User.last_name.ilike(term),
                User.email.ilike(term), User.phone.ilike(term)
            ))
        users = query.order_by(User.first_name.asc()).limit(int(request.args.get('limit', 300))).all()
        return success_response('Users fetched successfully',
                                [user.to_dict() for user in users], status_code=200)
    except Exception as e:
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['GET'])
@auth_required()
@require_permission('view')
def get_user(id):
    """Get user by ID (tenant scoped)"""
    try:
        user = _guest_query().filter(User.id == id).first()
        if not user:
            return error_response('User not found', 404)
        return success_response('User fetched successfully', user.to_dict(), status_code=200)
    except Exception as e:
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['PUT'])
@auth_required()
@require_permission('edit')
def update_user(id):
    """Update a guest profile (own profile, hotel staff with edit rights, or owner)"""
    try:
        current = get_current_user()
        target = db.session.get(User, id)
        if target is None:
            return error_response('User not found', 404)

        if target.id != current.id:
            if target.business_id != current_business_id() or not current.can('edit'):
                return error_response('Unauthorized', 403)

        data = request.get_json()
        if 'email' in data and data['email'] != target.email:
            if User.query.filter_by(email=data['email']).first():
                return error_response('This email is already registered', 400)
            target.email = data['email']
        for field in ('first_name', 'last_name', 'phone', 'nationality', 'address',
                      'id_type', 'id_number'):
            if field in data:
                setattr(target, field, data[field])
        if data.get('password'):
            if len(str(data['password'])) < 6:
                return error_response('Password must be at least 6 characters', 400)
            target.set_password(data['password'])

        target.updated_by = current.id
        db.session.commit()

        log_activity(ACTIVITY_UPDATE, 'guests', target.id, target.email,
                     f"Updated guest {target.first_name} {target.last_name}")
        return success_response('User updated successfully', target.to_dict(), status_code=200)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['DELETE'])
@auth_required()
@require_permission('delete')
def delete_user(id):
    """Delete a guest account (blocked while bookings exist so history is preserved)"""
    try:
        target = _guest_query().filter(User.id == id).first()
        if not target:
            return error_response('User not found', 404)

        bookings = RoomRecord.query.filter_by(user_id=target.id, is_deleted=False).count()
        if bookings:
            return error_response(
                f'This guest has {bookings} booking(s) and cannot be deleted. Booking history is kept.', 400
            )

        email = target.email
        db.session.delete(target)
        db.session.commit()

        log_activity(ACTIVITY_DELETE, 'guests', id, email, f"Deleted guest {email}")
        return success_response('User deleted successfully', status_code=200)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)
