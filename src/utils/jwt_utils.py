import jwt
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify
from config import Config


def encode_token(user_id, hours=None):
    """Encode JWT token with user ID"""
    if hours is None:
        hours = Config.JWT_EXPIRATION_HOURS
    
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(hours=hours),
        'iat': datetime.utcnow()
    }
    
    token = jwt.encode(
        payload,
        Config.JWT_SECRET_KEY,
        algorithm=Config.ALGORITHM
    )
    return token


def decode_token(token):
    """Decode JWT token and return user ID"""
    try:
        payload = jwt.decode(
            token,
            Config.JWT_SECRET_KEY,
            algorithms=[Config.ALGORITHM]
        )
        return payload.get('user_id')
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def token_required(f):
    """Decorator to protect routes with JWT authentication"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Check for token in headers
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(" ")[1]
            except IndexError:
                return jsonify({'message': 'Invalid token format'}), 401
        
        if not token:
            return jsonify({'message': 'Token is missing'}), 401
        
        user_id = decode_token(token)
        if user_id is None:
            return jsonify({'message': 'Token is invalid or expired'}), 401
        
        request.user_id = user_id
        return f(*args, **kwargs)
    
    return decorated
