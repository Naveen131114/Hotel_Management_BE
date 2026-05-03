from flask import Blueprint, request
from src import db
from src.models.accessories import Accessory
from src.utils import success_response, error_response, token_required

bp = Blueprint('accessories', __name__, url_prefix='/api/accessories')


@bp.route('', methods=['GET'])
def get_all_accessories():
    """Get all accessories with optional filters"""
    try:
        query = Accessory.query
        
        if request.args.get('accessory_type_id'):
            query = query.filter_by(accessory_type_id=request.args.get('accessory_type_id'))
        if request.args.get('is_chargeable'):
            is_chargeable = request.args.get('is_chargeable').lower() == 'true'
            query = query.filter_by(is_chargeable=is_chargeable)
        
        accessories = query.all()
        data = [accessory.to_dict() for accessory in accessories]
        return success_response('Accessories fetched successfully', data, status_code=200)
    except Exception as e:
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['GET'])
def get_accessory(id):
    """Get accessory by ID"""
    try:
        accessory = Accessory.query.get(id)
        if not accessory:
            return error_response('Accessory not found', 404)
        return success_response('Accessory fetched successfully', accessory.to_dict(), status_code=200)
    except Exception as e:
        return error_response(f'Error: {str(e)}', 500)


@bp.route('', methods=['POST'])
@token_required
def create_accessory():
    """Create a new accessory (protected)"""
    try:
        data = request.get_json()
        
        required_fields = ['name', 'accessory_type_id']
        if not all(field in data for field in required_fields):
            return error_response('Missing required fields', 400)
        
        accessory = Accessory(
            accessory_type_id=data['accessory_type_id'],
            name=data['name'],
            description=data.get('description'),
            unit=data.get('unit'),
            unit_price=data.get('unit_price', 0.00),
            is_chargeable=data.get('is_chargeable', False)
        )
        
        db.session.add(accessory)
        db.session.commit()
        
        return success_response('Accessory created successfully', accessory.to_dict(), status_code=201)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['PUT'])
@token_required
def update_accessory(id):
    """Update accessory (protected)"""
    try:
        accessory = Accessory.query.get(id)
        if not accessory:
            return error_response('Accessory not found', 404)
        
        data = request.get_json()
        
        if 'name' in data:
            accessory.name = data['name']
        if 'description' in data:
            accessory.description = data['description']
        if 'unit' in data:
            accessory.unit = data['unit']
        if 'unit_price' in data:
            accessory.unit_price = data['unit_price']
        if 'is_chargeable' in data:
            accessory.is_chargeable = data['is_chargeable']
        
        db.session.commit()
        
        return success_response('Accessory updated successfully', accessory.to_dict(), status_code=200)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['DELETE'])
@token_required
def delete_accessory(id):
    """Delete accessory (protected)"""
    try:
        accessory = Accessory.query.get(id)
        if not accessory:
            return error_response('Accessory not found', 404)
        
        db.session.delete(accessory)
        db.session.commit()
        
        return success_response('Accessory deleted successfully', status_code=200)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)
