from flask import jsonify


def success_response(message, data=None, token=None, status_code=200):
    """Generate a success response"""
    response = {
        'message': message,
    }
    
    if data is not None:
        response['data'] = data
    
    if token is not None:
        response['token'] = token
    
    return jsonify(response), status_code


def error_response(message, status_code=400):
    """Generate an error response"""
    response = {
        'message': message,
    }
    
    return jsonify(response), status_code
