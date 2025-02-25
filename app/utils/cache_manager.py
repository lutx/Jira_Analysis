from functools import wraps
from flask import current_app
from app.extensions import cache
import logging
import hashlib
import json

logger = logging.getLogger(__name__)

def cache_key_builder(*args, **kwargs):
    """Build a cache key from arguments."""
    key_parts = [str(arg) for arg in args]
    key_parts.extend(f"{k}:{v}" for k, v in sorted(kwargs.items()))
    key = ":".join(key_parts)
    return hashlib.md5(key.encode()).hexdigest()

def cached(timeout=300, key_prefix='view'):
    """Cache decorator with dynamic key generation."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            cache_key = f"{key_prefix}:{cache_key_builder(*args, **kwargs)}"
            
            # Try to get from cache
            response = cache.get(cache_key)
            if response:
                logger.debug(f"Cache hit for key: {cache_key}")
                return response
                
            # If not in cache, call the function
            logger.debug(f"Cache miss for key: {cache_key}")
            response = f(*args, **kwargs)
            
            # Store in cache
            try:
                cache.set(cache_key, response, timeout=timeout)
            except Exception as e:
                logger.error(f"Error caching response: {str(e)}")
                
            return response
        return decorated_function
    return decorator

def clear_cache_pattern(pattern):
    """Clear all cache keys matching pattern."""
    try:
        cache.delete_pattern(pattern)
        logger.info(f"Cleared cache for pattern: {pattern}")
        return True
    except Exception as e:
        logger.error(f"Error clearing cache pattern {pattern}: {str(e)}")
        return False 