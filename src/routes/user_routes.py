from flask import Blueprint, request
from src import db
from src.models.users import User
from src.utils import success_response, error_response, token_required

bp = Blueprint('users', __name__, url_prefix='/api/users')


@bp.route('', methods=['GET'])
def get_all_users():
    """Get all users"""
    try:
        users = User.query.all()
        data = [user.to_dict() for user in users]
        return success_response('Users fetched successfully', data, status_code=200)
    except Exception as e:
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['GET'])
def get_user(id):
    """Get user by ID"""
    try:
        user = User.query.get(id)
        if not user:
            return error_response('User not found', 404)
        return success_response('User fetched successfully', user.to_dict(), status_code=200)
    except Exception as e:
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['PUT'])
@token_required
def update_user(id):
    """Update user profile (protected)"""
    try:
        user = User.query.get(id)
        if not user:
            return error_response('User not found', 404)
        
        # Only allow users to update their own profile
        if user.id != request.user_id:
            return error_response('Unauthorized', 403)
        
        data = request.get_json()
        
        if 'first_name' in data:
            user.first_name = data['first_name']
        if 'last_name' in data:
            user.last_name = data['last_name']
        if 'phone' in data:
            user.phone = data['phone']
        if 'nationality' in data:
            user.nationality = data['nationality']
        if 'address' in data:
            user.address = data['address']
        
        db.session.commit()
        
        return success_response('User updated successfully', user.to_dict(), status_code=200)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['DELETE'])
@token_required
def delete_user(id):
    """Delete user account (protected)"""
    try:
        user = User.query.get(id)
        if not user:
            return error_response('User not found', 404)
        
        # Only allow users to delete their own account
        if user.id != request.user_id:
            return error_response('Unauthorized', 403)
        
        db.session.delete(user)
        db.session.commit()
        
        return success_response('User deleted successfully', status_code=200)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)
