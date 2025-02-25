from flask import request, current_app
from functools import wraps
import logging
import time

logger = logging.getLogger(__name__)

def log_request(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        start_time = time.time()
        
        # Log request
        logger.info(f"Request: {request.method} {request.path} from {request.remote_addr}")
        if current_app.debug:
            logger.debug(f"Headers: {dict(request.headers)}")
            logger.debug(f"Args: {request.args}")
            if request.is_json:
                logger.debug(f"JSON: {request.get_json()}")
        
        response = f(*args, **kwargs)
        
        # Log response
        duration = time.time() - start_time
        logger.info(f"Response: {response.status_code} in {duration:.2f}s")
        
        return response
    return decorated_function 