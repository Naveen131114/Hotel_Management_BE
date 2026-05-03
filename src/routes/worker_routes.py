from flask import Blueprint, request
from src import db
from src.models.workers import Worker
from src.utils import success_response, error_response, token_required

bp = Blueprint('workers', __name__, url_prefix='/api/workers')


@bp.route('', methods=['GET'])
def get_all_workers():
    """Get all workers with optional filters"""
    try:
        query = Worker.query
        
        if request.args.get('status'):
            query = query.filter_by(status=request.args.get('status'))
        if request.args.get('worker_type_id'):
            query = query.filter_by(worker_type_id=request.args.get('worker_type_id'))
        
        workers = query.all()
        data = [worker.to_dict() for worker in workers]
        return success_response('Workers fetched successfully', data, status_code=200)
    except Exception as e:
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['GET'])
def get_worker(id):
    """Get worker by ID"""
    try:
        worker = Worker.query.get(id)
        if not worker:
            return error_response('Worker not found', 404)
        return success_response('Worker fetched successfully', worker.to_dict(), status_code=200)
    except Exception as e:
        return error_response(f'Error: {str(e)}', 500)


@bp.route('', methods=['POST'])
@token_required
def create_worker():
    """Create a new worker (protected)"""
    try:
        data = request.get_json()
        
        required_fields = ['first_name', 'last_name', 'worker_type_id']
        if not all(field in data for field in required_fields):
            return error_response('Missing required fields', 400)
        
        worker = Worker(
            worker_type_id=data['worker_type_id'],
            first_name=data['first_name'],
            last_name=data['last_name'],
            email=data.get('email'),
            phone=data.get('phone'),
            national_id=data.get('national_id'),
            status=data.get('status', 'active'),
            hire_date=data.get('hire_date')
        )
        
        db.session.add(worker)
        db.session.commit()
        
        return success_response('Worker created successfully', worker.to_dict(), status_code=201)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['PUT'])
@token_required
def update_worker(id):
    """Update worker (protected)"""
    try:
        worker = Worker.query.get(id)
        if not worker:
            return error_response('Worker not found', 404)
        
        data = request.get_json()
        
        if 'first_name' in data:
            worker.first_name = data['first_name']
        if 'last_name' in data:
            worker.last_name = data['last_name']
        if 'email' in data:
            worker.email = data['email']
        if 'phone' in data:
            worker.phone = data['phone']
        if 'status' in data:
            worker.status = data['status']
        
        db.session.commit()
        
        return success_response('Worker updated successfully', worker.to_dict(), status_code=200)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['DELETE'])
@token_required
def delete_worker(id):
    """Delete worker (protected)"""
    try:
        worker = Worker.query.get(id)
        if not worker:
            return error_response('Worker not found', 404)
        
        db.session.delete(worker)
        db.session.commit()
        
        return success_response('Worker deleted successfully', status_code=200)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)
