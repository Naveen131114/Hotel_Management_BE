from flask import Blueprint, request

from src import db
from src.models.workers import Worker
from src.models.worker_types import WorkerType
from src.utils import (
    success_response, error_response, auth_required, require_permission, tenant_scope,
    resolve_branch_id, log_activity, get_current_user, current_business_id,
)
from src.utils.constants import ACTIVITY_CREATE, ACTIVITY_DELETE, ACTIVITY_UPDATE, MODULE_WORKERS

bp = Blueprint('workers', __name__, url_prefix='/api/workers')


@bp.route('', methods=['GET'])
@auth_required()
@require_permission('view')
def get_all_workers():
    """Get all workers of the current hotel/branch"""
    try:
        query = tenant_scope(Worker, Worker.query)
        if request.args.get('status'):
            query = query.filter_by(status=request.args.get('status'))
        if request.args.get('worker_type_id'):
            query = query.filter_by(worker_type_id=request.args.get('worker_type_id'))
        items = query.order_by(Worker.first_name.asc()).all()
        return success_response('Workers fetched successfully',
                                [item.to_dict() for item in items], status_code=200)
    except Exception as e:
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['GET'])
@auth_required()
@require_permission('view')
def get_worker(id):
    """Get worker by ID (tenant scoped)"""
    try:
        item = tenant_scope(Worker, Worker.query).filter(Worker.id == id).first()
        if not item:
            return error_response('Worker not found', 404)
        return success_response('Worker fetched successfully', item.to_dict(), status_code=200)
    except Exception as e:
        return error_response(f'Error: {str(e)}', 500)


@bp.route('', methods=['POST'])
@auth_required()
@require_permission('create')
def create_worker():
    """Create a worker (non-login staff record)"""
    try:
        data = request.get_json()
        if not data.get('first_name') or not data.get('last_name') or not data.get('worker_type_id'):
            return error_response('First name, last name and worker_type_id are required', 400)

        business_id = current_business_id()
        worker_type = WorkerType.query.filter_by(id=data['worker_type_id'], business_id=business_id).first()
        if worker_type is None:
            return error_response('Worker type not found for this hotel', 404)

        if data.get('email') and Worker.query.filter_by(email=data['email']).first():
            return error_response('A worker with this email already exists', 400)

        branch_id, error = resolve_branch_id(data.get('branch_id'))
        if error:
            return error

        user = get_current_user()
        item = Worker(
            business_id=business_id,
            branch_id=branch_id,
            worker_type_id=worker_type.id,
            first_name=data['first_name'],
            last_name=data['last_name'],
            email=data.get('email'),
            phone=data.get('phone'),
            national_id=data.get('national_id'),
            hire_date=data.get('hire_date'),
            status=data.get('status', 'active'),
            created_by=user.id if user else None
        )
        db.session.add(item)
        db.session.commit()

        log_activity(ACTIVITY_CREATE, MODULE_WORKERS, item.id, f"{item.first_name} {item.last_name}",
                     f"Created worker {item.first_name} {item.last_name}", branch_id=item.branch_id)
        return success_response('Worker created successfully', item.to_dict(), status_code=201)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)



@bp.route('/<int:id>', methods=['PUT'])
@auth_required()
@require_permission('edit')
def update_worker(id):
    """Update a worker"""
    try:
        item = tenant_scope(Worker, Worker.query).filter(Worker.id == id).first()
        if not item:
            return error_response('Worker not found', 404)

        data = request.get_json()
        if 'worker_type_id' in data:
            worker_type = WorkerType.query.filter_by(
                id=data['worker_type_id'], business_id=item.business_id
            ).first()
            if worker_type is None:
                return error_response('Worker type not found for this hotel', 404)
            item.worker_type_id = worker_type.id
        if data.get('email') and data['email'] != item.email:
            if Worker.query.filter_by(email=data['email']).first():
                return error_response('A worker with this email already exists', 400)
        for field in ('first_name', 'last_name', 'email', 'phone', 'national_id',
                      'hire_date', 'status'):
            if field in data:
                setattr(item, field, data[field])
        if 'branch_id' in data:
            branch_id, error = resolve_branch_id(data['branch_id'])
            if error:
                return error
            item.branch_id = branch_id

        item.updated_by = get_current_user().id
        db.session.commit()

        log_activity(ACTIVITY_UPDATE, MODULE_WORKERS, item.id, f"{item.first_name} {item.last_name}",
                     f"Updated worker {item.first_name} {item.last_name}", branch_id=item.branch_id)
        return success_response('Worker updated successfully', item.to_dict(), status_code=200)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['DELETE'])
@auth_required()
@require_permission('delete')
def delete_worker(id):
    """Delete a worker (deactivated instead when linked to bookings/maintenance)"""
    try:
        item = tenant_scope(Worker, Worker.query).filter(Worker.id == id).first()
        if not item:
            return error_response('Worker not found', 404)

        linked = len(item.room_records) + len(item.maintenance_logs)
        if linked:
            item.status = 'inactive'
            db.session.commit()
            return success_response(
                f'This worker is linked to {linked} record(s), so they were marked inactive instead of deleted',
                item.to_dict(), status_code=200
            )

        name = f"{item.first_name} {item.last_name}"
        db.session.delete(item)
        db.session.commit()

        log_activity(ACTIVITY_DELETE, MODULE_WORKERS, id, name, f"Deleted worker {name}")
        return success_response('Worker deleted successfully', status_code=200)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)
