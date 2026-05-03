from flask import Blueprint, request
from src import db
from src.models.users import User
from src.utils import success_response, error_response, encode_token

bp = Blueprint('auth', __name__, url_prefix='/api/auth')


@bp.route('/register', methods=['POST'])
def register():
    """Register a new user"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['first_name', 'last_name', 'email', 'password']
        if not all(field in data for field in required_fields):
            return error_response('Missing required fields', 400)
        
        # Check if user already exists
        if User.query.filter_by(email=data['email']).first():
            return error_response('User already exists', 400)
        
        # Create new user
        user = User(
            first_name=data['first_name'],
            last_name=data['last_name'],
            email=data['email'],
            phone=data.get('phone'),
            id_number=data.get('id_number'),
            id_type=data.get('id_type'),
            nationality=data.get('nationality'),
            address=data.get('address')
        )
        user.set_password(data['password'])
        
        db.session.add(user)
        db.session.commit()
        
        # Generate token
        token = encode_token(user.id)
        
        return success_response('User registered successfully', user.to_dict(), token, 201)
    
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/login', methods=['POST'])
def login():
    """Login user"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('email') or not data.get('password'):
            return error_response('Email and password required', 400)
        
        # Find user
        user = User.query.filter_by(email=data['email']).first()
        if not user or not user.check_password(data['password']):
            return error_response('Invalid email or password', 401)
        
        # Generate token
        token = encode_token(user.id)
        
        return success_response('Login successful', user.to_dict(), token, 200)
    
    except Exception as e:
        return error_response(f'Error: {str(e)}', 500)
