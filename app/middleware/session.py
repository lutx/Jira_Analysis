from functools import wraps
from flask import session, request, abort, current_app
import logging

logger = logging.getLogger(__name__)

def check_session(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method != 'GET':
            if 'csrf_token' not in session:
                logger.warning('CSRF token missing in session')
                abort(400, description="CSRF token missing")
            logger.debug(f"CSRF token in session: {session.get('csrf_token')}")
        return f(*args, **kwargs)
    return decorated_function 