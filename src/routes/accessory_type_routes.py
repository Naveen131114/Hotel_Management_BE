from flask import Blueprint, request

from src import db
from src.models.accessory_types import AccessoryType
from src.models.accessories import Accessory
from src.utils import (
    success_response, error_response, auth_required, require_permission, tenant_scope,
    log_activity, get_current_user, current_business_id,
)
from src.utils.constants import (
    ACTIVITY_CREATE, ACTIVITY_DELETE, ACTIVITY_UPDATE, MODULE_ACCESSORY_TYPES,
)

bp = Blueprint('accessory_types', __name__, url_prefix='/api/accessory-types')


@bp.route('', methods=['GET'])
@auth_required()
@require_permission('view')
def get_all_accessory_types():
    """Get all accessory types of the current hotel"""
    try:
        types = tenant_scope(AccessoryType, AccessoryType.query).order_by(AccessoryType.name.asc()).all()
        return success_response('Accessory types fetched successfully',
                                [item.to_dict() for item in types], status_code=200)
    except Exception as e:
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['GET'])
@auth_required()
@require_permission('view')
def get_accessory_type(id):
    """Get accessory type by ID (tenant scoped)"""
    try:
        item = tenant_scope(AccessoryType, AccessoryType.query).filter(AccessoryType.id == id).first()
        if not item:
            return error_response('Accessory type not found', 404)
        return success_response('Accessory type fetched successfully', item.to_dict(), status_code=200)
    except Exception as e:
        return error_response(f'Error: {str(e)}', 500)


@bp.route('', methods=['POST'])
@auth_required()
@require_permission('create')
def create_accessory_type():
    """Create an accessory type"""
    try:
        data = request.get_json()
        if not data.get('name'):
            return error_response('Name is required', 400)

        user = get_current_user()
        item = AccessoryType(
            business_id=current_business_id(),
            name=data['name'],
            description=data.get('description'),
            created_by=user.id if user else None
        )
        db.session.add(item)
        db.session.commit()

        log_activity(ACTIVITY_CREATE, MODULE_ACCESSORY_TYPES, item.id, item.name,
                     f"Created accessory type {item.name}")
        return success_response('Accessory type created successfully', item.to_dict(), status_code=201)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['PUT'])
@auth_required()
@require_permission('edit')
def update_accessory_type(id):
    """Update an accessory type"""
    try:
        item = tenant_scope(AccessoryType, AccessoryType.query).filter(AccessoryType.id == id).first()
        if not item:
            return error_response('Accessory type not found', 404)

        data = request.get_json()
        if 'name' in data:
            item.name = data['name']
        if 'description' in data:
            item.description = data['description']
        item.updated_by = get_current_user().id
        db.session.commit()

        log_activity(ACTIVITY_UPDATE, MODULE_ACCESSORY_TYPES, item.id, item.name,
                     f"Updated accessory type {item.name}")
        return success_response('Accessory type updated successfully', item.to_dict(), status_code=200)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['DELETE'])
@auth_required()
@require_permission('delete')
def delete_accessory_type(id):
    """Delete an accessory type (blocked while accessories use it)"""
    try:
        item = tenant_scope(AccessoryType, AccessoryType.query).filter(AccessoryType.id == id).first()
        if not item:
            return error_response('Accessory type not found', 404)

        in_use = Accessory.query.filter_by(accessory_type_id=item.id).count()
        if in_use:
            return error_response(f'{in_use} accessory(ies) use this type. Delete or move them first.', 400)

        name = item.name
        db.session.delete(item)
        db.session.commit()

        log_activity(ACTIVITY_DELETE, MODULE_ACCESSORY_TYPES, id, name, f"Deleted accessory type {name}")
        return success_response('Accessory type deleted successfully', status_code=200)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)
