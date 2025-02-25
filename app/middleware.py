# Globalny handler błędów
# Middleware do walidacji żądań
# Middleware do rate limitingu 

from functools import wraps
from flask import request, jsonify, current_app, g
from flask_wtf.csrf import validate_csrf, generate_csrf
from app.exceptions import ValidationError
import logging
import time

logger = logging.getLogger(__name__)

# Tymczasowo zakomentowane do czasu instalacji Flask-Limiter
# from flask_limiter import Limiter
# from flask_limiter.util import get_remote_address
# 
# limiter = Limiter(
#     key_func=get_remote_address,
#     default_limits=["200 per day", "50 per hour"]
# )

def log_csrf_attempt(e):
    """Loguje próby ataku CSRF."""
    logger.warning(
        'CSRF Attack Attempt',
        extra={
            'ip': request.remote_addr,
            'path': request.path,
            'method': request.method,
            'user_agent': request.user_agent.string
        }
    )
    return jsonify({
        'error': 'CSRF validation failed',
        'message': 'Invalid or missing CSRF token'
    }), 400

def csrf_protect():
    """Dekorator do ochrony CSRF."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
                csrf_token = request.headers.get('X-CSRF-Token')
                if not csrf_token:
                    log_csrf_attempt(None)
                    raise ValidationError("Brak tokenu CSRF")
                try:
                    validate_csrf(csrf_token)
                except Exception as e:
                    log_csrf_attempt(e)
                    raise ValidationError("Nieprawidłowy token CSRF")
            return f(*args, **kwargs)
        return decorated_function
    return decorator 

def configure_rate_limits(app):
    """Tymczasowo wyłączone rate limiting"""
    @app.route('/api/csrf-token')
    def get_csrf_token():
        token = generate_csrf()
        return jsonify({'csrf_token': token})

    # Dodaj endpoint do app
    app.add_url_rule('/api/csrf-token', 'get_csrf_token', get_csrf_token) 

def setup_middleware(app):
    @app.before_request
    def before_request():
        g.start_time = time.time()
        
    @app.after_request
    def after_request(response):
        if hasattr(g, 'start_time'):
            elapsed = time.time() - g.start_time
            logger.info(f"Request to {request.path} took {elapsed:.2f}s")
        return response
        
    @app.teardown_request
    def teardown_request(exception=None):
        if exception:
            logger.error(f"Request failed: {str(exception)}") 