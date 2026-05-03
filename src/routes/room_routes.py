from flask import Blueprint, request
from src import db
from src.models.rooms import Room
from src.utils import success_response, error_response, token_required

bp = Blueprint('rooms', __name__, url_prefix='/api/rooms')


@bp.route('', methods=['GET'])
def get_all_rooms():
    """Get all rooms with optional filters"""
    try:
        query = Room.query
        
        # Apply filters
        if request.args.get('status'):
            query = query.filter_by(status=request.args.get('status'))
        if request.args.get('floor'):
            query = query.filter_by(floor=request.args.get('floor'))
        if request.args.get('room_type_id'):
            query = query.filter_by(room_type_id=request.args.get('room_type_id'))
        
        rooms = query.all()
        data = [room.to_dict() for room in rooms]
        return success_response('Rooms fetched successfully', data, status_code=200)
    except Exception as e:
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['GET'])
def get_room(id):
    """Get room by ID"""
    try:
        room = Room.query.get(id)
        if not room:
            return error_response('Room not found', 404)
        return success_response('Room fetched successfully', room.to_dict(), status_code=200)
    except Exception as e:
        return error_response(f'Error: {str(e)}', 500)


@bp.route('', methods=['POST'])
@token_required
def create_room():
    """Create a new room (protected)"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['room_type_id', 'room_number', 'floor']
        if not all(field in data for field in required_fields):
            return error_response('Missing required fields', 400)
        
        # Check if room already exists
        if Room.query.filter_by(room_number=data['room_number']).first():
            return error_response('Room number already exists', 400)
        
        room = Room(
            room_type_id=data['room_type_id'],
            room_number=data['room_number'],
            floor=data['floor'],
            status=data.get('status', 'available'),
            notes=data.get('notes')
        )
        
        db.session.add(room)
        db.session.commit()
        
        return success_response('Room created successfully', room.to_dict(), status_code=201)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['PUT'])
@token_required
def update_room(id):
    """Update room (protected)"""
    try:
        room = Room.query.get(id)
        if not room:
            return error_response('Room not found', 404)
        
        data = request.get_json()
        
        # Update fields
        if 'room_type_id' in data:
            room.room_type_id = data['room_type_id']
        if 'room_number' in data:
            room.room_number = data['room_number']
        if 'floor' in data:
            room.floor = data['floor']
        if 'status' in data:
            room.status = data['status']
        if 'notes' in data:
            room.notes = data['notes']
        
        db.session.commit()
        
        return success_response('Room updated successfully', room.to_dict(), status_code=200)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['DELETE'])
@token_required
def delete_room(id):
    """Delete room (protected)"""
    try:
        room = Room.query.get(id)
        if not room:
            return error_response('Room not found', 404)
        
        db.session.delete(room)
        db.session.commit()
        
        return success_response('Room deleted successfully', status_code=200)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)
