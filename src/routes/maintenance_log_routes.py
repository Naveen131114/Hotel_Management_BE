from datetime import datetime

from flask import Blueprint, request

from src import db
from src.models.maintenance_logs import MaintenanceLog
from src.models.rooms import Room
from src.models.workers import Worker
from src.utils import (
    success_response, error_response, auth_required, require_permission, tenant_scope,
    log_activity, get_current_user,
)
from src.utils.constants import ACTIVITY_CREATE, ACTIVITY_DELETE, ACTIVITY_UPDATE

bp = Blueprint('maintenance_logs', __name__, url_prefix='/api/maintenance-logs')


def _scoped(query):
    """Maintenance logs inherit the tenant scope through their room"""
    return query.filter(MaintenanceLog.room_id.in_(
        tenant_scope(Room, Room.query).with_entities(Room.id)
    ))


@bp.route('', methods=['GET'])
@auth_required()
@require_permission('view')
def get_all_maintenance_logs():
    """Get maintenance logs of the current hotel with optional filters"""
    try:
        query = _scoped(MaintenanceLog.query)
        if request.args.get('room_id'):
            query = query.filter_by(room_id=request.args.get('room_id'))
        if request.args.get('status'):
            query = query.filter_by(status=request.args.get('status'))

        logs = query.order_by(MaintenanceLog.created_at.desc()).all()
        return success_response('Maintenance logs fetched successfully',
                                [log.to_dict() for log in logs], status_code=200)
    except Exception as e:
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['GET'])
@auth_required()
@require_permission('view')
def get_maintenance_log(id):
    """Get a maintenance log by ID (tenant scoped)"""
    try:
        log = _scoped(MaintenanceLog.query).filter(MaintenanceLog.id == id).first()
        if not log:
            return error_response('Maintenance log not found', 404)
        return success_response('Maintenance log fetched successfully', log.to_dict(), status_code=200)
    except Exception as e:
        return error_response(f'Error: {str(e)}', 500)


@bp.route('', methods=['POST'])
@auth_required()
@require_permission('create')
def create_maintenance_log():
    """Report a room issue (the room is set to maintenance when requested)"""
    try:
        data = request.get_json()
        if not data.get('room_id'):
            return error_response('room_id is required', 400)

        room = tenant_scope(Room, Room.query).filter(Room.id == data['room_id']).first()
        if not room:
            return error_response('Room not found', 404)

        worker_id = data.get('worker_id')
        if worker_id:
            worker = Worker.query.filter_by(id=worker_id, business_id=room.business_id).first()
            if worker is None:
                return error_response('Worker not found for this hotel', 404)

        log = MaintenanceLog(
            room_id=room.id,
            worker_id=worker_id,
            issue_type=data.get('issue_type'),
            description=data.get('description'),
            status=data.get('status', 'reported'),
            started_at=data.get('started_at')
        )
        db.session.add(log)

        if data.get('set_room_maintenance'):
            room.status = 'maintenance'
        db.session.commit()

        log_activity(ACTIVITY_CREATE, 'maintenance', log.id, room.room_number,
                     f"Reported maintenance for room {room.room_number}", branch_id=room.branch_id)
        return success_response('Maintenance log created successfully', log.to_dict(), status_code=201)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['PUT'])
@auth_required()
@require_permission('edit')
def update_maintenance_log(id):
    """Update a maintenance log (resolve it and free the room)"""
    try:
        log = _scoped(MaintenanceLog.query).filter(MaintenanceLog.id == id).first()
        if not log:
            return error_response('Maintenance log not found', 404)

        data = request.get_json()
        for field in ('worker_id', 'issue_type', 'description', 'status', 'started_at'):
            if field in data:
                setattr(log, field, data[field])
        if data.get('status') == 'resolved':
            log.resolved_at = log.resolved_at or datetime.utcnow()
            if log.room is not None and log.room.status == 'maintenance':
                log.room.status = 'available'
        db.session.commit()

        log_activity(ACTIVITY_UPDATE, 'maintenance', log.id, None, f"Updated maintenance log #{log.id}")
        return success_response('Maintenance log updated successfully', log.to_dict(), status_code=200)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['DELETE'])
@auth_required()
@require_permission('delete')
def delete_maintenance_log(id):
    """Delete a maintenance log"""
    try:
        log = _scoped(MaintenanceLog.query).filter(MaintenanceLog.id == id).first()
        if not log:
            return error_response('Maintenance log not found', 404)

        db.session.delete(log)
        db.session.commit()

        log_activity(ACTIVITY_DELETE, 'maintenance', id, None, f"Deleted maintenance log #{id}")
        return success_response('Maintenance log deleted successfully', status_code=200)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)
