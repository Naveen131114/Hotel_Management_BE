from flask import Blueprint, request
from src import db
from src.models.room_types import RoomType
from src.utils import success_response, error_response, token_required

bp = Blueprint('room_types', __name__, url_prefix='/api/room-types')


@bp.route('', methods=['GET'])
def get_all_room_types():
    """Get all room types"""
    try:
        room_types = RoomType.query.filter_by(is_active=True).all()
        data = [rt.to_dict() for rt in room_types]
        return success_response('Room types fetched successfully', data, status_code=200)
    except Exception as e:
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['GET'])
def get_room_type(id):
    """Get room type by ID"""
    try:
        room_type = RoomType.query.get(id)
        if not room_type:
            return error_response('Room type not found', 404)
        return success_response('Room type fetched successfully', room_type.to_dict(), status_code=200)
    except Exception as e:
        return error_response(f'Error: {str(e)}', 500)


@bp.route('', methods=['POST'])
@token_required
def create_room_type():
    """Create a new room type (protected)"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('name') or not data.get('base_price'):
            return error_response('Name and base_price required', 400)
        
        room_type = RoomType(
            name=data['name'],
            description=data.get('description'),
            base_price=data['base_price'],
            max_occupancy=data.get('max_occupancy', 2),
            total_floors=data.get('total_floors', 1),
            bed_type=data.get('bed_type'),
            view_type=data.get('view_type')
        )
        
        db.session.add(room_type)
        db.session.commit()
        
        return success_response('Room type created successfully', room_type.to_dict(), status_code=201)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['PUT'])
@token_required
def update_room_type(id):
    """Update room type (protected)"""
    try:
        room_type = RoomType.query.get(id)
        if not room_type:
            return error_response('Room type not found', 404)
        
        data = request.get_json()
        
        # Update fields
        if 'name' in data:
            room_type.name = data['name']
        if 'description' in data:
            room_type.description = data['description']
        if 'base_price' in data:
            room_type.base_price = data['base_price']
        if 'max_occupancy' in data:
            room_type.max_occupancy = data['max_occupancy']
        if 'total_floors' in data:
            room_type.total_floors = data['total_floors']
        if 'bed_type' in data:
            room_type.bed_type = data['bed_type']
        if 'view_type' in data:
            room_type.view_type = data['view_type']
        if 'is_active' in data:
            room_type.is_active = data['is_active']
        
        db.session.commit()
        
        return success_response('Room type updated successfully', room_type.to_dict(), status_code=200)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['DELETE'])
@token_required
def delete_room_type(id):
    """Delete room type (protected)"""
    try:
        room_type = RoomType.query.get(id)
        if not room_type:
            return error_response('Room type not found', 404)
        
        db.session.delete(room_type)
        db.session.commit()
        
        return success_response('Room type deleted successfully', status_code=200)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)
