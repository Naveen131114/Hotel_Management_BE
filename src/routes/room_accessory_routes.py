from flask import Blueprint, request

from src import db
from src.models.room_accessories import RoomAccessory
from src.models.rooms import Room
from src.models.accessories import Accessory
from src.utils import (
    success_response, error_response, auth_required, require_permission, tenant_scope,
    log_activity, get_current_user,
)
from src.utils.constants import ACTIVITY_CREATE, ACTIVITY_DELETE, ACTIVITY_UPDATE

bp = Blueprint('room_accessories', __name__, url_prefix='/api/room-accessories')


def _scoped(query):
    """Room-accessory records inherit the tenant scope through their room"""
    return query.filter(RoomAccessory.room_id.in_(
        tenant_scope(Room, Room.query).with_entities(Room.id)
    ))


@bp.route('', methods=['GET'])
@auth_required()
@require_permission('view')
def get_all_room_accessories():
    """Get accessories assigned to rooms of the current hotel"""
    try:
        query = _scoped(RoomAccessory.query)
        if request.args.get('room_id'):
            query = query.filter_by(room_id=request.args.get('room_id'))
        items = query.all()
        return success_response('Room accessories fetched successfully',
                                [item.to_dict() for item in items], status_code=200)
    except Exception as e:
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['GET'])
@auth_required()
@require_permission('view')
def get_room_accessory(id):
    """Get a room-accessory record by ID (tenant scoped)"""
    try:
        item = _scoped(RoomAccessory.query).filter(RoomAccessory.id == id).first()
        if not item:
            return error_response('Room accessory not found', 404)
        return success_response('Room accessory fetched successfully', item.to_dict(), status_code=200)
    except Exception as e:
        return error_response(f'Error: {str(e)}', 500)


@bp.route('', methods=['POST'])
@auth_required()
@require_permission('create')
def create_room_accessory():
    """Assign an accessory to a room (room and accessory must belong to the hotel)"""
    try:
        data = request.get_json()
        if not data.get('room_id') or not data.get('accessory_id'):
            return error_response('room_id and accessory_id are required', 400)

        room = tenant_scope(Room, Room.query).filter(Room.id == data['room_id']).first()
        if not room:
            return error_response('Room not found', 404)

        accessory = Accessory.query.filter_by(id=data['accessory_id'], business_id=room.business_id).first()
        if accessory is None:
            return error_response('Accessory not found for this hotel', 404)

        existing = RoomAccessory.query.filter_by(room_id=room.id, accessory_id=accessory.id).first()
        if existing:
            existing.quantity = data.get('quantity', existing.quantity)
            existing.condition = data.get('condition', existing.condition)
            db.session.commit()
            return success_response('Room accessory updated successfully', existing.to_dict(), status_code=200)

        item = RoomAccessory(
            room_id=room.id,
            accessory_id=accessory.id,
            quantity=data.get('quantity', 1),
            condition=data.get('condition', 'good')
        )
        db.session.add(item)
        db.session.commit()

        log_activity(ACTIVITY_CREATE, 'room_accessories', item.id, room.room_number,
                     f"Assigned accessory {accessory.name} to room {room.room_number}",
                     branch_id=room.branch_id)
        return success_response('Room accessory created successfully', item.to_dict(), status_code=201)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['PUT'])
@auth_required()
@require_permission('edit')
def update_room_accessory(id):
    """Update a room-accessory record"""
    try:
        item = _scoped(RoomAccessory.query).filter(RoomAccessory.id == id).first()
        if not item:
            return error_response('Room accessory not found', 404)

        data = request.get_json()
        for field in ('quantity', 'condition'):
            if field in data:
                setattr(item, field, data[field])
        db.session.commit()

        log_activity(ACTIVITY_UPDATE, 'room_accessories', item.id, None,
                     f"Updated room accessory #{item.id}", branch_id=item.room.branch_id if item.room else None)
        return success_response('Room accessory updated successfully', item.to_dict(), status_code=200)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['DELETE'])
@auth_required()
@require_permission('delete')
def delete_room_accessory(id):
    """Remove an accessory from a room"""
    try:
        item = _scoped(RoomAccessory.query).filter(RoomAccessory.id == id).first()
        if not item:
            return error_response('Room accessory not found', 404)

        db.session.delete(item)
        db.session.commit()

        log_activity(ACTIVITY_DELETE, 'room_accessories', id, None, f"Removed room accessory #{id}")
        return success_response('Room accessory deleted successfully', status_code=200)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)
