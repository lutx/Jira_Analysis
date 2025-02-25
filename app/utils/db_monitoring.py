from flask import current_app
import logging
import time
from functools import wraps

logger = logging.getLogger(__name__)

def log_slow_queries(threshold_ms=500):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            start_time = time.time()
            result = f(*args, **kwargs)
            duration = (time.time() - start_time) * 1000
            
            if duration > threshold_ms:
                logger.warning(
                    f"Slow query detected in {f.__name__}: {duration:.2f}ms"
                )
            
            return result
        return wrapped
    return decorator 