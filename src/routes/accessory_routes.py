from flask import Blueprint, request

from src import db
from src.models.accessories import Accessory
from src.models.accessory_types import AccessoryType
from src.utils import (
    success_response, error_response, auth_required, require_permission, tenant_scope,
    log_activity, get_current_user, current_business_id,
)
from src.utils.constants import ACTIVITY_CREATE, ACTIVITY_DELETE, ACTIVITY_UPDATE, MODULE_ACCESSORIES

bp = Blueprint('accessories', __name__, url_prefix='/api/accessories')


@bp.route('', methods=['GET'])
@auth_required()
@require_permission('view')
def get_all_accessories():
    """Get all accessories of the current hotel"""
    try:
        query = tenant_scope(Accessory, Accessory.query)
        if request.args.get('accessory_type_id'):
            query = query.filter_by(accessory_type_id=request.args.get('accessory_type_id'))
        if request.args.get('chargeable_only') in ('1', 'true'):
            query = query.filter(Accessory.is_chargeable.is_(True))
        items = query.order_by(Accessory.name.asc()).all()
        return success_response('Accessories fetched successfully',
                                [item.to_dict() for item in items], status_code=200)
    except Exception as e:
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['GET'])
@auth_required()
@require_permission('view')
def get_accessory(id):
    """Get accessory by ID (tenant scoped)"""
    try:
        item = tenant_scope(Accessory, Accessory.query).filter(Accessory.id == id).first()
        if not item:
            return error_response('Accessory not found', 404)
        return success_response('Accessory fetched successfully', item.to_dict(), status_code=200)
    except Exception as e:
        return error_response(f'Error: {str(e)}', 500)


@bp.route('', methods=['POST'])
@auth_required()
@require_permission('create')
def create_accessory():
    """Create an accessory"""
    try:
        data = request.get_json()
        if not data.get('name') or not data.get('accessory_type_id'):
            return error_response('Name and accessory_type_id are required', 400)

        business_id = current_business_id()
        accessory_type = AccessoryType.query.filter_by(id=data['accessory_type_id'], business_id=business_id).first()
        if accessory_type is None:
            return error_response('Accessory type not found for this hotel', 404)

        user = get_current_user()
        item = Accessory(
            business_id=business_id,
            accessory_type_id=accessory_type.id,
            name=data['name'],
            description=data.get('description'),
            unit=data.get('unit'),
            unit_price=data.get('unit_price', 0),
            is_chargeable=data.get('is_chargeable', False),
            created_by=user.id if user else None
        )
        db.session.add(item)
        db.session.commit()

        log_activity(ACTIVITY_CREATE, MODULE_ACCESSORIES, item.id, item.name,
                     f"Created accessory {item.name}")
        return success_response('Accessory created successfully', item.to_dict(), status_code=201)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['PUT'])
@auth_required()
@require_permission('edit')
def update_accessory(id):
    """Update an accessory"""
    try:
        item = tenant_scope(Accessory, Accessory.query).filter(Accessory.id == id).first()
        if not item:
            return error_response('Accessory not found', 404)

        data = request.get_json()
        if 'accessory_type_id' in data:
            accessory_type = AccessoryType.query.filter_by(
                id=data['accessory_type_id'], business_id=item.business_id
            ).first()
            if accessory_type is None:
                return error_response('Accessory type not found for this hotel', 404)
            item.accessory_type_id = accessory_type.id
        for field in ('name', 'description', 'unit', 'unit_price', 'is_chargeable'):
            if field in data:
                setattr(item, field, data[field])
        item.updated_by = get_current_user().id
        db.session.commit()

        log_activity(ACTIVITY_UPDATE, MODULE_ACCESSORIES, item.id, item.name,
                     f"Updated accessory {item.name}")
        return success_response('Accessory updated successfully', item.to_dict(), status_code=200)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['DELETE'])
@auth_required()
@require_permission('delete')
def delete_accessory(id):
    """Delete an accessory (assigned room/bookings links are removed with it)"""
    try:
        item = tenant_scope(Accessory, Accessory.query).filter(Accessory.id == id).first()
        if not item:
            return error_response('Accessory not found', 404)

        name = item.name
        db.session.delete(item)
        db.session.commit()

        log_activity(ACTIVITY_DELETE, MODULE_ACCESSORIES, id, name, f"Deleted accessory {name}")
        return success_response('Accessory deleted successfully', status_code=200)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)
