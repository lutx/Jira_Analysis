import time
import traceback
import logging
import functools
from contextlib import contextmanager
from typing import Dict, Any, Optional, Callable
from datetime import datetime
from flask import current_app, request

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

logger = logging.getLogger(__name__)

class Monitor:
    def __init__(self):
        self.metrics = {}
        self.start_times = {}
        self.memory_usage = {}
        self.query_counts = {}

    @contextmanager
    def measure(self, name: str):
        """Measure execution time of a code block."""
        start_time = time.time()
        try:
            yield
        finally:
            end_time = time.time()
            duration = end_time - start_time
            
            if name not in self.metrics:
                self.metrics[name] = []
            self.metrics[name].append(duration)
            
            logger.info(f"Operation '{name}' took {duration:.3f} seconds")

    @contextmanager
    def measure_memory(self, name: str):
        """Measure memory usage of a code block."""
        if not HAS_PSUTIL:
            yield
            return
            
        process = psutil.Process()
        start_memory = process.memory_info().rss
        try:
            yield
        finally:
            end_memory = process.memory_info().rss
            memory_used = end_memory - start_memory
            
            if name not in self.memory_usage:
                self.memory_usage[name] = []
            self.memory_usage[name].append(memory_used)
            
            logger.info(f"Operation '{name}' used {memory_used/1024/1024:.2f} MB")

    @contextmanager
    def measure_queries(self, name: str):
        """Measure number of database queries in a code block."""
        start_count = self._get_query_count()
        try:
            yield
        finally:
            end_count = self._get_query_count()
            query_count = end_count - start_count
            
            if name not in self.query_counts:
                self.query_counts[name] = []
            self.query_counts[name].append(query_count)
            
            logger.info(f"Operation '{name}' executed {query_count} queries")

    def _get_query_count(self) -> int:
        """Get current database query count."""
        # This is a placeholder - implement based on your ORM
        return 0

    def measure_time(self, name: Optional[str] = None) -> Callable:
        """Decorator to measure function execution time."""
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                operation_name = name or func.__name__
                with self.measure(operation_name):
                    return func(*args, **kwargs)
            return wrapper
        return decorator

    def get_metrics(self) -> Dict[str, Any]:
        """Get collected metrics."""
        return {
            'execution_times': {
                name: {
                    'avg': sum(times)/len(times),
                    'min': min(times),
                    'max': max(times),
                    'count': len(times)
                }
                for name, times in self.metrics.items()
            },
            'memory_usage': {
                name: {
                    'avg': sum(usage)/len(usage)/1024/1024,
                    'min': min(usage)/1024/1024,
                    'max': max(usage)/1024/1024,
                    'count': len(usage)
                }
                for name, usage in self.memory_usage.items()
            },
            'query_counts': {
                name: {
                    'avg': sum(counts)/len(counts),
                    'min': min(counts),
                    'max': max(counts),
                    'count': len(counts)
                }
                for name, counts in self.query_counts.items()
            }
        }

    def reset(self):
        """Reset all metrics."""
        self.metrics.clear()
        self.memory_usage.clear()
        self.query_counts.clear()

# Create global monitor instance
monitor = Monitor()

def init_monitoring(app):
    """Initialize monitoring for Flask app."""
    @app.before_request
    def before_request():
        request._start_time = time.time()
        request._start_memory = psutil.Process().memory_info().rss

    @app.after_request
    def after_request(response):
        if hasattr(request, '_start_time'):
            duration = time.time() - request._start_time
            memory_used = psutil.Process().memory_info().rss - request._start_memory
            
            logger.info(
                f"Request {request.endpoint} completed in {duration:.3f}s "
                f"using {memory_used/1024/1024:.2f}MB"
            )
            
            # Add timing headers
            response.headers['X-Response-Time'] = f"{duration:.3f}s"
            response.headers['X-Memory-Usage'] = f"{memory_used/1024/1024:.2f}MB"
        
        return response

    @app.cli.command('show-metrics')
    def show_metrics():
        """Show collected metrics."""
        metrics = monitor.get_metrics()
        current_app.logger.info("Application Metrics:")
        for category, data in metrics.items():
            current_app.logger.info(f"\n{category}:")
            for name, stats in data.items():
                current_app.logger.info(f"  {name}:")
                for stat, value in stats.items():
                    current_app.logger.info(f"    {stat}: {value}")

class StatsMonitor:
    """Klasa do monitorowania wydajności statystyk."""
    
    def __init__(self):
        self.metrics = {}
        self.start_time = datetime.now()
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Pobiera statystyki systemowe."""
        stats = {
            'timestamp': datetime.now().isoformat()
        }
        
        if HAS_PSUTIL:
            try:
                stats.update({
                    'cpu_percent': psutil.cpu_percent(),
                    'memory_percent': psutil.virtual_memory().percent,
                    'disk_usage': psutil.disk_usage('/').percent
                })
            except Exception as e:
                logger.error(f"Error getting system stats: {str(e)}")
        
        return stats
    
    def _init_metric(self, name: str) -> None:
        """Inicjalizuje metryki dla danej operacji."""
        if name not in self.metrics:
            self.metrics[name] = {
                'count': 0,
                'total_time': 0,
                'avg_time': 0,
                'error_count': 0,
                'last_error': None,
                'memory_used': 0,
                'peak_memory': 0,
                'query_count': 0,
                'slow_queries': []
            }
    
    @contextmanager
    def measure(self, name: str):
        """Context manager do mierzenia czasu wykonania."""
        self._init_metric(name)
        start_time = time.time()
        
        try:
            yield
        except Exception as e:
            self.metrics[name]['error_count'] += 1
            self.metrics[name]['last_error'] = f"{type(e).__name__}: {str(e)}"
            logger.error(f"Error in {name}: {traceback.format_exc()}")
            raise
        finally:
            execution_time = time.time() - start_time
            self.metrics[name]['count'] += 1
            self.metrics[name]['total_time'] += execution_time
            self.metrics[name]['avg_time'] = (
                self.metrics[name]['total_time'] / self.metrics[name]['count']
            )
    
    @contextmanager
    def measure_memory(self, name: str):
        """Context manager do mierzenia zużycia pamięci."""
        self._init_metric(name)
        process = psutil.Process()
        start_memory = process.memory_info().rss
        
        try:
            yield
        finally:
            end_memory = process.memory_info().rss
            memory_used = end_memory - start_memory
            self.metrics[name]['memory_used'] = memory_used
            self.metrics[name]['peak_memory'] = max(
                self.metrics[name]['peak_memory'],
                memory_used
            )
    
    @contextmanager
    def measure_queries(self, name: str, slow_query_threshold: float = 1.0):
        """Context manager do mierzenia zapytań do bazy danych."""
        self._init_metric(name)
        query_count = 0
        slow_queries = []
        
        def query_callback(query):
            nonlocal query_count
            start_time = time.time()
            result = query()
            execution_time = time.time() - start_time
            
            query_count += 1
            if execution_time > slow_query_threshold:
                slow_queries.append({
                    'query': str(query),
                    'time': execution_time
                })
            
            return result
        
        try:
            with current_app.db.query_callback(query_callback):
                yield
        finally:
            self.metrics[name]['query_count'] = query_count
            self.metrics[name]['slow_queries'].extend(slow_queries)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Zwraca zebrane metryki."""
        return self.metrics
    
    def export_metrics(self) -> Dict[str, Any]:
        """Eksportuje metryki do formatu JSON."""
        return {
            'timestamp': datetime.now().isoformat(),
            'start_time': self.start_time.isoformat(),
            'metrics': self.metrics
        }
    
    def reset(self) -> None:
        """Resetuje wszystkie metryki."""
        self.metrics = {}
        self.start_time = datetime.now()

class SecurityMonitor:
    def __init__(self):
        self.csrf_attempts = 0
        self.last_csrf_attempt = None
        self.rate_limit_hits = 0
        self.blocked_ips = set()
        
    def log_csrf_attempt(self, request_info: dict):
        """Loguje próbę ataku CSRF."""
        self.csrf_attempts += 1
        self.last_csrf_attempt = {
            'timestamp': datetime.now(),
            'request': request_info
        }
        
        # Alert jeśli dużo prób
        if self.csrf_attempts > 10:
            self.alert_security_team()
    
    def log_rate_limit_hit(self, request_info: dict):
        """Loguje przekroczenie limitu requestów."""
        self.rate_limit_hits += 1
        ip = request_info.get('ip')
        if ip:
            self.blocked_ips.add(ip)
            
        if self.rate_limit_hits > 100:  # Dużo prób
            self.alert_security_team('High rate limit violations detected')
    
    def alert_security_team(self):
        """Wysyła alert do zespołu bezpieczeństwa."""
        # Implementacja alertów
        pass
    
    def get_security_metrics(self) -> dict:
        """Zwraca metryki bezpieczeństwa."""
        return {
            'csrf_attempts': self.csrf_attempts,
            'rate_limit_hits': self.rate_limit_hits,
            'blocked_ips_count': len(self.blocked_ips),
            'last_csrf_attempt': self.last_csrf_attempt
        }

# Metryki wydajności
# Alerty o problemach
# Dashboard z metrykami 