import time
import logging
from functools import wraps
from flask import request, g
from app.extensions import cache

logger = logging.getLogger(__name__)

def measure_time(name=None):
    """Decorator to measure execution time of functions."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Start timing
            start = time.time()
            
            # Execute function
            result = f(*args, **kwargs)
            
            # Calculate execution time
            execution_time = time.time() - start
            
            # Log if execution time exceeds threshold
            if execution_time > current_app.config.get('SLOW_EXECUTION_THRESHOLD', 1.0):
                logger.warning(
                    f"Slow execution detected: {name or f.__name__} "
                    f"took {execution_time:.2f} seconds"
                )
            
            # Store metrics
            metric_key = f"metrics:{name or f.__name__}"
            try:
                metrics = cache.get(metric_key) or {
                    'count': 0,
                    'total_time': 0,
                    'max_time': 0
                }
                
                metrics['count'] += 1
                metrics['total_time'] += execution_time
                metrics['max_time'] = max(metrics['max_time'], execution_time)
                
                cache.set(metric_key, metrics)
                
            except Exception as e:
                logger.error(f"Error storing metrics: {str(e)}")
            
            return result
        return decorated_function
    return decorator

def get_performance_metrics():
    """Get all stored performance metrics."""
    try:
        metrics = {}
        for key in cache.scan_iter("metrics:*"):
            metric_name = key.split(":", 1)[1]
            metric_data = cache.get(key)
            if metric_data:
                metrics[metric_name] = {
                    'count': metric_data['count'],
                    'avg_time': metric_data['total_time'] / metric_data['count'],
                    'max_time': metric_data['max_time']
                }
        return metrics
    except Exception as e:
        logger.error(f"Error getting performance metrics: {str(e)}")
        return {} 