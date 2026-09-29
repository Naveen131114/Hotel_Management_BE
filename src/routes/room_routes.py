from flask import Blueprint, request

from src import db
from src.models.rooms import Room
from src.models.room_types import RoomType
from src.models.room_records import RoomRecord
from src.services import subscription_service
from src.utils import (
    success_response, error_response, auth_required, require_permission, tenant_scope,
    resolve_branch_id, log_activity, get_current_user, current_business_id,
)
from src.utils.constants import (
    ACTIVITY_CREATE, ACTIVITY_DELETE, ACTIVITY_UPDATE, MODULE_ROOMS, ROOM_STATUSES,
)

bp = Blueprint('rooms', __name__, url_prefix='/api/rooms')


@bp.route('', methods=['GET'])
@auth_required()
@require_permission('view')
def get_all_rooms():
    """Get all rooms of the current hotel/branch with optional filters"""
    try:
        query = tenant_scope(Room, Room.query)

        if request.args.get('status'):
            query = query.filter_by(status=request.args.get('status'))
        if request.args.get('floor'):
            query = query.filter_by(floor=request.args.get('floor'))
        if request.args.get('room_type_id'):
            query = query.filter_by(room_type_id=request.args.get('room_type_id'))
        if request.args.get('online_only') in ('1', 'true'):
            query = query.filter(Room.is_online_bookable.is_(True))

        rooms = query.order_by(Room.room_number.asc()).all()
        return success_response('Rooms fetched successfully', [room.to_dict() for room in rooms], status_code=200)
    except Exception as e:
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['GET'])
@auth_required()
@require_permission('view')
def get_room(id):
    """Get room by ID (tenant scoped)"""
    try:
        room = tenant_scope(Room, Room.query).filter(Room.id == id).first()
        if not room:
            return error_response('Room not found', 404)
        return success_response('Room fetched successfully', room.to_dict(), status_code=200)
    except Exception as e:
        return error_response(f'Error: {str(e)}', 500)


@bp.route('', methods=['POST'])
@auth_required()
@require_permission('create')
def create_room():
    """Create a new room (branch + subscription room limit enforced)"""
    try:
        data = request.get_json()

        required_fields = ['room_type_id', 'room_number', 'floor']
        if not all(field in data for field in required_fields):
            return error_response('Missing required fields', 400)

        business_id = current_business_id()
        allowed, message, usage, limits = subscription_service.check_limit(business_id, 'room')
        if not allowed:
            return error_response(message, 403)

        room_type = RoomType.query.filter_by(id=data['room_type_id'], business_id=business_id).first()
        if room_type is None:
            return error_response('Room type not found for this hotel', 404)

        branch_id, error = resolve_branch_id(data.get('branch_id') or room_type.branch_id)
        if error:
            return error
        if branch_id is None:
            return error_response('branch_id is required (select a branch first)', 400)

        if Room.query.filter_by(branch_id=branch_id, room_number=data['room_number']).first():
            return error_response('Room number already exists in this branch', 400)

        user = get_current_user()
        room = Room(
            room_type_id=room_type.id,
            business_id=business_id,
            branch_id=branch_id,
            room_number=data['room_number'],
            name=data.get('name'),
            floor=data['floor'],
            capacity=int(data.get('capacity') or room_type.max_occupancy or 2),
            base_price=data.get('base_price') if data.get('base_price') not in (None, '') else room_type.base_price,
            extra_guest_price=data.get('extra_guest_price', 0),
            description=data.get('description'),
            image_url=data.get('image_url'),
            is_online_bookable=data.get('is_online_bookable', True),
            status=data.get('status', 'available'),
            notes=data.get('notes'),
            created_by=user.id if user else None
        )

        db.session.add(room)
        db.session.commit()

        log_activity(ACTIVITY_CREATE, MODULE_ROOMS, room.id, room.room_number,
                     f"Created room {room.room_number}", branch_id=room.branch_id)
        payload = room.to_dict()
        payload['subscription_usage'] = {**usage, 'room_limit': limits.get('max_rooms')}
        return success_response('Room created successfully', payload, status_code=201)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)



@bp.route('/<int:id>', methods=['PUT'])
@auth_required()
@require_permission('edit')
def update_room(id):
    """Update room (tenant scoped)"""
    try:
        room = tenant_scope(Room, Room.query).filter(Room.id == id).first()
        if not room:
            return error_response('Room not found', 404)

        data = request.get_json()

        if 'room_type_id' in data:
            room_type = RoomType.query.filter_by(id=data['room_type_id'], business_id=room.business_id).first()
            if room_type is None:
                return error_response('Room type not found for this hotel', 404)
            room.room_type_id = room_type.id
        if 'room_number' in data:
            duplicate = Room.query.filter(
                Room.branch_id == room.branch_id,
                Room.room_number == data['room_number'],
                Room.id != room.id
            ).first()
            if duplicate:
                return error_response('Room number already exists in this branch', 400)
            room.room_number = data['room_number']
        if 'floor' in data:
            room.floor = data['floor']
        if 'status' in data:
            if data['status'] not in ROOM_STATUSES:
                return error_response('Invalid room status', 400)
            room.status = data['status']
        for field in ('name', 'capacity', 'base_price', 'extra_guest_price', 'description',
                      'image_url', 'is_online_bookable', 'notes'):
            if field in data:
                setattr(room, field, data[field])
        if 'branch_id' in data:
            branch_id, error = resolve_branch_id(data['branch_id'])
            if error:
                return error
            room.branch_id = branch_id

        room.updated_by = get_current_user().id
        db.session.commit()

        log_activity(ACTIVITY_UPDATE, MODULE_ROOMS, room.id, room.room_number,
                     f"Updated room {room.room_number}", branch_id=room.branch_id)
        return success_response('Room updated successfully', room.to_dict(), status_code=200)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['DELETE'])
@auth_required()
@require_permission('delete')
def delete_room(id):
    """Delete room (blocked while bookings exist so history is preserved)"""
    try:
        room = tenant_scope(Room, Room.query).filter(Room.id == id).first()
        if not room:
            return error_response('Room not found', 404)

        bookings = RoomRecord.query.filter_by(room_id=room.id, is_deleted=False).count()
        if bookings:
            return error_response(
                f'This room has {bookings} booking(s). Set the room to maintenance/blocked instead of deleting it.', 400
            )

        room_number = room.room_number
        db.session.delete(room)
        db.session.commit()

        log_activity(ACTIVITY_DELETE, MODULE_ROOMS, id, room_number, f"Deleted room {room_number}")
        return success_response('Room deleted successfully', status_code=200)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)
