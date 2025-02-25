from functools import wraps
from flask import request, abort, current_app
from flask_wtf.csrf import CSRFError
import logging

logger = logging.getLogger(__name__)

def csrf_protect():
    """CSRF protection middleware."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if request.method not in ['GET', 'HEAD', 'OPTIONS', 'TRACE']:
                if not current_app.config.get('WTF_CSRF_CHECK_DEFAULT', True):
                    return f(*args, **kwargs)
                try:
                    csrf.protect()
                except CSRFError as e:
                    logger.warning(f"CSRF validation failed: {str(e)}")
                    abort(400, description="CSRF validation failed")
            return f(*args, **kwargs)
        return decorated_function
    return decorator 