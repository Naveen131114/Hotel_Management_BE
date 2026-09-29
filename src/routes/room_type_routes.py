from flask import Blueprint, request

from src import db
from src.models.room_types import RoomType
from src.models.rooms import Room
from src.utils import (
    success_response, error_response, auth_required, require_permission, tenant_scope,
    resolve_branch_id, log_activity, get_current_user, current_business_id,
)
from src.utils.constants import (
    ACTIVITY_CREATE, ACTIVITY_DELETE, ACTIVITY_UPDATE, MODULE_ROOM_TYPES,
)

bp = Blueprint('room_types', __name__, url_prefix='/api/room-types')


@bp.route('', methods=['GET'])
@auth_required()
@require_permission('view')
def get_all_room_types():
    """Get all room types of the current hotel"""
    try:
        query = tenant_scope(RoomType, RoomType.query)
        if request.args.get('include_inactive') not in ('1', 'true'):
            query = query.filter(RoomType.is_active.is_(True))
        room_types = query.order_by(RoomType.base_price.asc()).all()
        return success_response('Room types fetched successfully',
                                [rt.to_dict() for rt in room_types], status_code=200)
    except Exception as e:
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['GET'])
@auth_required()
@require_permission('view')
def get_room_type(id):
    """Get room type by ID (tenant scoped)"""
    try:
        room_type = tenant_scope(RoomType, RoomType.query).filter(RoomType.id == id).first()
        if not room_type:
            return error_response('Room type not found', 404)
        return success_response('Room type fetched successfully', room_type.to_dict(), status_code=200)
    except Exception as e:
        return error_response(f'Error: {str(e)}', 500)


@bp.route('', methods=['POST'])
@auth_required()
@require_permission('create')
def create_room_type():
    """Create a new room type"""
    try:
        data = request.get_json()

        if not data.get('name') or not data.get('base_price'):
            return error_response('Name and base_price required', 400)

        branch_id, error = resolve_branch_id(data.get('branch_id'))
        if error:
            return error

        user = get_current_user()
        room_type = RoomType(
            business_id=current_business_id(),
            branch_id=branch_id,
            name=data['name'],
            description=data.get('description'),
            base_price=data['base_price'],
            extra_guest_price=data.get('extra_guest_price', 0),
            max_occupancy=data.get('max_occupancy', 2),
            total_floors=data.get('total_floors', 1),
            bed_type=data.get('bed_type'),
            view_type=data.get('view_type'),
            image_url=data.get('image_url'),
            is_online_bookable=data.get('is_online_bookable', True),
            created_by=user.id if user else None
        )

        db.session.add(room_type)
        db.session.commit()

        log_activity(ACTIVITY_CREATE, MODULE_ROOM_TYPES, room_type.id, room_type.name,
                     f"Created room type {room_type.name}", branch_id=room_type.branch_id)
        return success_response('Room type created successfully', room_type.to_dict(), status_code=201)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['PUT'])
@auth_required()
@require_permission('edit')
def update_room_type(id):
    """Update room type (tenant scoped)"""
    try:
        room_type = tenant_scope(RoomType, RoomType.query).filter(RoomType.id == id).first()
        if not room_type:
            return error_response('Room type not found', 404)

        data = request.get_json()
        for field in ('name', 'description', 'base_price', 'extra_guest_price', 'max_occupancy',
                      'total_floors', 'bed_type', 'view_type', 'image_url',
                      'is_online_bookable', 'is_active'):
            if field in data:
                setattr(room_type, field, data[field])
        room_type.updated_by = get_current_user().id
        db.session.commit()

        log_activity(ACTIVITY_UPDATE, MODULE_ROOM_TYPES, room_type.id, room_type.name,
                     f"Updated room type {room_type.name}")
        return success_response('Room type updated successfully', room_type.to_dict(), status_code=200)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['DELETE'])
@auth_required()
@require_permission('delete')
def delete_room_type(id):
    """Delete room type (deactivated instead when rooms still use it)"""
    try:
        room_type = tenant_scope(RoomType, RoomType.query).filter(RoomType.id == id).first()
        if not room_type:
            return error_response('Room type not found', 404)

        in_use = Room.query.filter_by(room_type_id=room_type.id).count()
        if in_use:
            room_type.is_active = False
            db.session.commit()
            return success_response(
                f'{in_use} room(s) use this room type, so it was deactivated instead of deleted',
                room_type.to_dict(), status_code=200
            )

        name = room_type.name
        db.session.delete(room_type)
        db.session.commit()

        log_activity(ACTIVITY_DELETE, MODULE_ROOM_TYPES, id, name, f"Deleted room type {name}")
        return success_response('Room type deleted successfully', status_code=200)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)
