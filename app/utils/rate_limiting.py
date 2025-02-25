from flask import request, current_app
from functools import wraps
import time
from cachetools import TTLCache

# Cache for storing request counts
requests_cache = TTLCache(maxsize=1000, ttl=60)  # 60 seconds TTL

def rate_limit(max_requests=100, window=60):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            key = f"{request.remote_addr}:{request.endpoint}"
            current_time = time.time()
            
            # Get request history
            requests = requests_cache.get(key, [])
            
            # Clean old requests
            requests = [req_time for req_time in requests 
                       if current_time - req_time < window]
            
            if len(requests) >= max_requests:
                return {'error': 'Too many requests'}, 429
            
            requests.append(current_time)
            requests_cache[key] = requests
            
            return f(*args, **kwargs)
        return wrapped
    return decorator 