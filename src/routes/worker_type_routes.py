from flask import Blueprint, request

from src import db
from src.models.worker_types import WorkerType
from src.models.workers import Worker
from src.utils import (
    success_response, error_response, auth_required, require_permission, tenant_scope,
    log_activity, get_current_user, current_business_id,
)
from src.utils.constants import ACTIVITY_CREATE, ACTIVITY_DELETE, ACTIVITY_UPDATE, MODULE_WORKER_TYPES

bp = Blueprint('worker_types', __name__, url_prefix='/api/worker-types')


@bp.route('', methods=['GET'])
@auth_required()
@require_permission('view')
def get_all_worker_types():
    """Get all worker types of the current hotel"""
    try:
        items = tenant_scope(WorkerType, WorkerType.query).order_by(WorkerType.title.asc()).all()
        return success_response('Worker types fetched successfully',
                                [item.to_dict() for item in items], status_code=200)
    except Exception as e:
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['GET'])
@auth_required()
@require_permission('view')
def get_worker_type(id):
    """Get worker type by ID (tenant scoped)"""
    try:
        item = tenant_scope(WorkerType, WorkerType.query).filter(WorkerType.id == id).first()
        if not item:
            return error_response('Worker type not found', 404)
        return success_response('Worker type fetched successfully', item.to_dict(), status_code=200)
    except Exception as e:
        return error_response(f'Error: {str(e)}', 500)


@bp.route('', methods=['POST'])
@auth_required()
@require_permission('create')
def create_worker_type():
    """Create a worker type (receptionist, cleaner, manager, security ...)"""
    try:
        data = request.get_json()
        if not data.get('title'):
            return error_response('Title is required', 400)

        user = get_current_user()
        item = WorkerType(
            business_id=current_business_id(),
            title=data['title'],
            description=data.get('description'),
            base_salary=data.get('base_salary'),
            created_by=user.id if user else None
        )
        db.session.add(item)
        db.session.commit()

        log_activity(ACTIVITY_CREATE, MODULE_WORKER_TYPES, item.id, item.title,
                     f"Created worker type {item.title}")
        return success_response('Worker type created successfully', item.to_dict(), status_code=201)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['PUT'])
@auth_required()
@require_permission('edit')
def update_worker_type(id):
    """Update a worker type"""
    try:
        item = tenant_scope(WorkerType, WorkerType.query).filter(WorkerType.id == id).first()
        if not item:
            return error_response('Worker type not found', 404)

        data = request.get_json()
        for field in ('title', 'description', 'base_salary'):
            if field in data:
                setattr(item, field, data[field])
        item.updated_by = get_current_user().id
        db.session.commit()

        log_activity(ACTIVITY_UPDATE, MODULE_WORKER_TYPES, item.id, item.title,
                     f"Updated worker type {item.title}")
        return success_response('Worker type updated successfully', item.to_dict(), status_code=200)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['DELETE'])
@auth_required()
@require_permission('delete')
def delete_worker_type(id):
    """Delete a worker type (blocked while workers use it)"""
    try:
        item = tenant_scope(WorkerType, WorkerType.query).filter(WorkerType.id == id).first()
        if not item:
            return error_response('Worker type not found', 404)

        in_use = Worker.query.filter_by(worker_type_id=item.id).count()
        if in_use:
            return error_response(f'{in_use} worker(s) use this type. Move or delete them first.', 400)

        title = item.title
        db.session.delete(item)
        db.session.commit()

        log_activity(ACTIVITY_DELETE, MODULE_WORKER_TYPES, id, title, f"Deleted worker type {title}")
        return success_response('Worker type deleted successfully', status_code=200)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)
