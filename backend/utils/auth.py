from functools import wraps
from flask import request, jsonify, current_app
import jwt
from backend.config import Config

def token_required(f):
    """
    Decorator to protect routes with JWT authentication.
    Passes current_user_id and current_user_role to the decorated function.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        
        # Fallback to Cookie
        if not token:
            token = request.cookies.get('token')
            
        if not token:
            return jsonify({'message': 'Token is missing'}), 401
        
        try:
            token = token.replace('Bearer ', '') if token.startswith('Bearer ') else token
            
            # Use current_app config if available, else fallback to Config class
            secret = current_app.config.get('JWT_SECRET_KEY', Config.JWT_SECRET_KEY)
            
            data = jwt.decode(token, secret, algorithms=['HS256'])
            current_user_id = data['user_id']
            current_user_role = data['role']
        except Exception as e:
            return jsonify({'message': 'Token is invalid'}), 401
        
        return f(current_user_id, current_user_role, *args, **kwargs)
    return decorated
