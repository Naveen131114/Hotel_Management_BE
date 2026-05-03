from flask import Blueprint, request
from src import db
from src.models.worker_types import WorkerType
from src.utils import success_response, error_response, token_required

bp = Blueprint('worker_types', __name__, url_prefix='/api/worker-types')


@bp.route('', methods=['GET'])
def get_all_worker_types():
    """Get all worker types"""
    try:
        worker_types = WorkerType.query.all()
        data = [wt.to_dict() for wt in worker_types]
        return success_response('Worker types fetched successfully', data, status_code=200)
    except Exception as e:
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['GET'])
def get_worker_type(id):
    """Get worker type by ID"""
    try:
        worker_type = WorkerType.query.get(id)
        if not worker_type:
            return error_response('Worker type not found', 404)
        return success_response('Worker type fetched successfully', worker_type.to_dict(), status_code=200)
    except Exception as e:
        return error_response(f'Error: {str(e)}', 500)


@bp.route('', methods=['POST'])
@token_required
def create_worker_type():
    """Create a new worker type (protected)"""
    try:
        data = request.get_json()
        
        if not data.get('title'):
            return error_response('Title required', 400)
        
        worker_type = WorkerType(
            title=data['title'],
            description=data.get('description'),
            base_salary=data.get('base_salary')
        )
        
        db.session.add(worker_type)
        db.session.commit()
        
        return success_response('Worker type created successfully', worker_type.to_dict(), status_code=201)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['PUT'])
@token_required
def update_worker_type(id):
    """Update worker type (protected)"""
    try:
        worker_type = WorkerType.query.get(id)
        if not worker_type:
            return error_response('Worker type not found', 404)
        
        data = request.get_json()
        
        if 'title' in data:
            worker_type.title = data['title']
        if 'description' in data:
            worker_type.description = data['description']
        if 'base_salary' in data:
            worker_type.base_salary = data['base_salary']
        
        db.session.commit()
        
        return success_response('Worker type updated successfully', worker_type.to_dict(), status_code=200)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['DELETE'])
@token_required
def delete_worker_type(id):
    """Delete worker type (protected)"""
    try:
        worker_type = WorkerType.query.get(id)
        if not worker_type:
            return error_response('Worker type not found', 404)
        
        db.session.delete(worker_type)
        db.session.commit()
        
        return success_response('Worker type deleted successfully', status_code=200)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)
