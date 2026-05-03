from flask import Blueprint, request
from src import db
from src.models.maintenance_logs import MaintenanceLog
from src.utils import success_response, error_response, token_required

bp = Blueprint('maintenance_logs', __name__, url_prefix='/api/maintenance-logs')


@bp.route('', methods=['GET'])
def get_all_maintenance_logs():
    """Get all maintenance logs with optional filters"""
    try:
        query = MaintenanceLog.query
        
        if request.args.get('room_id'):
            query = query.filter_by(room_id=request.args.get('room_id'))
        if request.args.get('status'):
            query = query.filter_by(status=request.args.get('status'))
        if request.args.get('issue_type'):
            query = query.filter_by(issue_type=request.args.get('issue_type'))
        
        logs = query.all()
        data = [log.to_dict() for log in logs]
        return success_response('Maintenance logs fetched successfully', data, status_code=200)
    except Exception as e:
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['GET'])
def get_maintenance_log(id):
    """Get maintenance log by ID"""
    try:
        log = MaintenanceLog.query.get(id)
        if not log:
            return error_response('Maintenance log not found', 404)
        return success_response('Maintenance log fetched successfully', log.to_dict(), status_code=200)
    except Exception as e:
        return error_response(f'Error: {str(e)}', 500)


@bp.route('', methods=['POST'])
@token_required
def create_maintenance_log():
    """Create a new maintenance log (protected)"""
    try:
        data = request.get_json()
        
        if not data.get('room_id'):
            return error_response('room_id required', 400)
        
        log = MaintenanceLog(
            room_id=data['room_id'],
            worker_id=data.get('worker_id'),
            issue_type=data.get('issue_type'),
            description=data.get('description'),
            status=data.get('status', 'reported'),
            started_at=data.get('started_at'),
            resolved_at=data.get('resolved_at')
        )
        
        db.session.add(log)
        db.session.commit()
        
        return success_response('Maintenance log created successfully', log.to_dict(), status_code=201)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['PUT'])
@token_required
def update_maintenance_log(id):
    """Update maintenance log (protected)"""
    try:
        log = MaintenanceLog.query.get(id)
        if not log:
            return error_response('Maintenance log not found', 404)
        
        data = request.get_json()
        
        if 'worker_id' in data:
            log.worker_id = data['worker_id']
        if 'issue_type' in data:
            log.issue_type = data['issue_type']
        if 'description' in data:
            log.description = data['description']
        if 'status' in data:
            log.status = data['status']
        if 'started_at' in data:
            log.started_at = data['started_at']
        if 'resolved_at' in data:
            log.resolved_at = data['resolved_at']
        
        db.session.commit()
        
        return success_response('Maintenance log updated successfully', log.to_dict(), status_code=200)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['DELETE'])
@token_required
def delete_maintenance_log(id):
    """Delete maintenance log (protected)"""
    try:
        log = MaintenanceLog.query.get(id)
        if not log:
            return error_response('Maintenance log not found', 404)
        
        db.session.delete(log)
        db.session.commit()
        
        return success_response('Maintenance log deleted successfully', status_code=200)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)
