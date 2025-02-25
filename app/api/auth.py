from functools import wraps
from flask import request, jsonify
from flask_login import current_user

def api_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({
                'error': 'unauthorized',
                'message': 'Authentication required'
            }), 401
        return f(*args, **kwargs)
    return decorated_function

def api_admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            return jsonify({
                'error': 'forbidden',
                'message': 'Admin privileges required'
            }), 403
        return f(*args, **kwargs)
    return decorated_function 