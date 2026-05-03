from flask import Blueprint, request
from src import db
from src.models.accessory_types import AccessoryType
from src.utils import success_response, error_response, token_required

bp = Blueprint('accessory_types', __name__, url_prefix='/api/accessory-types')


@bp.route('', methods=['GET'])
def get_all_accessory_types():
    """Get all accessory types"""
    try:
        types = AccessoryType.query.all()
        data = [t.to_dict() for t in types]
        return success_response('Accessory types fetched successfully', data, status_code=200)
    except Exception as e:
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['GET'])
def get_accessory_type(id):
    """Get accessory type by ID"""
    try:
        accessory_type = AccessoryType.query.get(id)
        if not accessory_type:
            return error_response('Accessory type not found', 404)
        return success_response('Accessory type fetched successfully', accessory_type.to_dict(), status_code=200)
    except Exception as e:
        return error_response(f'Error: {str(e)}', 500)


@bp.route('', methods=['POST'])
@token_required
def create_accessory_type():
    """Create a new accessory type (protected)"""
    try:
        data = request.get_json()
        
        if not data.get('name'):
            return error_response('Name required', 400)
        
        accessory_type = AccessoryType(
            name=data['name'],
            description=data.get('description')
        )
        
        db.session.add(accessory_type)
        db.session.commit()
        
        return success_response('Accessory type created successfully', accessory_type.to_dict(), status_code=201)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['PUT'])
@token_required
def update_accessory_type(id):
    """Update accessory type (protected)"""
    try:
        accessory_type = AccessoryType.query.get(id)
        if not accessory_type:
            return error_response('Accessory type not found', 404)
        
        data = request.get_json()
        
        if 'name' in data:
            accessory_type.name = data['name']
        if 'description' in data:
            accessory_type.description = data['description']
        
        db.session.commit()
        
        return success_response('Accessory type updated successfully', accessory_type.to_dict(), status_code=200)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['DELETE'])
@token_required
def delete_accessory_type(id):
    """Delete accessory type (protected)"""
    try:
        accessory_type = AccessoryType.query.get(id)
        if not accessory_type:
            return error_response('Accessory type not found', 404)
        
        db.session.delete(accessory_type)
        db.session.commit()
        
        return success_response('Accessory type deleted successfully', status_code=200)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)
