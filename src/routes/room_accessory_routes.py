from flask import Blueprint, request
from src import db
from src.models.room_accessories import RoomAccessory
from src.utils import success_response, error_response, token_required

bp = Blueprint('room_accessories', __name__, url_prefix='/api/room-accessories')


@bp.route('', methods=['GET'])
def get_all_room_accessories():
    """Get all room accessories with optional filters"""
    try:
        query = RoomAccessory.query
        
        if request.args.get('room_id'):
            query = query.filter_by(room_id=request.args.get('room_id'))
        if request.args.get('condition'):
            query = query.filter_by(condition=request.args.get('condition'))
        
        room_accessories = query.all()
        data = [ra.to_dict() for ra in room_accessories]
        return success_response('Room accessories fetched successfully', data, status_code=200)
    except Exception as e:
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['GET'])
def get_room_accessory(id):
    """Get room accessory by ID"""
    try:
        room_accessory = RoomAccessory.query.get(id)
        if not room_accessory:
            return error_response('Room accessory not found', 404)
        return success_response('Room accessory fetched successfully', room_accessory.to_dict(), status_code=200)
    except Exception as e:
        return error_response(f'Error: {str(e)}', 500)


@bp.route('', methods=['POST'])
@token_required
def create_room_accessory():
    """Create a new room accessory (protected)"""
    try:
        data = request.get_json()
        
        required_fields = ['room_id', 'accessory_id']
        if not all(field in data for field in required_fields):
            return error_response('Missing required fields', 400)
        
        # Check if already exists
        existing = RoomAccessory.query.filter_by(
            room_id=data['room_id'],
            accessory_id=data['accessory_id']
        ).first()
        
        if existing:
            return error_response('Room accessory already exists', 400)
        
        room_accessory = RoomAccessory(
            room_id=data['room_id'],
            accessory_id=data['accessory_id'],
            quantity=data.get('quantity', 1),
            condition=data.get('condition', 'good')
        )
        
        db.session.add(room_accessory)
        db.session.commit()
        
        return success_response('Room accessory created successfully', room_accessory.to_dict(), status_code=201)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['PUT'])
@token_required
def update_room_accessory(id):
    """Update room accessory (protected)"""
    try:
        room_accessory = RoomAccessory.query.get(id)
        if not room_accessory:
            return error_response('Room accessory not found', 404)
        
        data = request.get_json()
        
        if 'quantity' in data:
            room_accessory.quantity = data['quantity']
        if 'condition' in data:
            room_accessory.condition = data['condition']
        
        db.session.commit()
        
        return success_response('Room accessory updated successfully', room_accessory.to_dict(), status_code=200)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['DELETE'])
@token_required
def delete_room_accessory(id):
    """Delete room accessory (protected)"""
    try:
        room_accessory = RoomAccessory.query.get(id)
        if not room_accessory:
            return error_response('Room accessory not found', 404)
        
        db.session.delete(room_accessory)
        db.session.commit()
        
        return success_response('Room accessory deleted successfully', status_code=200)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)
