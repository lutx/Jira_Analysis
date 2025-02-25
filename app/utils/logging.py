import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional
from flask import request, g, current_app
from functools import wraps

# Konfiguracja loggera
logger = logging.getLogger(__name__)

class TeamStatsLogger:
    """Klasa do logowania zdarzeń w module statystyk zespołu."""
    
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Inicjalizuje logger dla aplikacji."""
        self.app = app
        
        # Konfiguracja handlera dla pliku
        file_handler = logging.FileHandler('team_stats.log')
        file_handler.setLevel(logging.INFO)
        
        # Format logów
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        
        # Dodaj handler do loggera
        logger.addHandler(file_handler)
        
        # Ustaw poziom logowania z konfiguracji
        logger.setLevel(app.config.get('LOG_LEVEL', logging.INFO))

def log_api_call(func):
    """Dekorator do logowania wywołań API."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = datetime.now()
        
        # Zbierz informacje o żądaniu
        request_info = {
            'method': request.method,
            'path': request.path,
            'args': dict(request.args),
            'user': getattr(g, 'user', None),
            'timestamp': start_time.isoformat()
        }
        
        try:
            # Wykonaj funkcję
            result = func(*args, **kwargs)
            
            # Oblicz czas wykonania
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Zaloguj sukces
            logger.info(
                'API Call Success',
                extra={
                    'request': request_info,
                    'execution_time': execution_time,
                    'status_code': getattr(result, 'status_code', 200)
                }
            )
            
            return result
            
        except Exception as e:
            # Zaloguj błąd
            logger.error(
                'API Call Error',
                extra={
                    'request': request_info,
                    'error': str(e),
                    'error_type': type(e).__name__
                },
                exc_info=True
            )
            raise
            
    return wrapper

def log_stats_generation(stats_type: str):
    """Dekorator do logowania generowania statystyk."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = datetime.now()
            
            # Zbierz informacje o generowaniu statystyk
            stats_info = {
                'type': stats_type,
                'args': args,
                'kwargs': kwargs,
                'timestamp': start_time.isoformat()
            }
            
            try:
                # Wykonaj funkcję
                result = func(*args, **kwargs)
                
                # Oblicz czas wykonania
                execution_time = (datetime.now() - start_time).total_seconds()
                
                # Zaloguj sukces
                logger.info(
                    'Stats Generation Success',
                    extra={
                        'stats': stats_info,
                        'execution_time': execution_time,
                        'result_size': len(str(result))
                    }
                )
                
                return result
                
            except Exception as e:
                # Zaloguj błąd
                logger.error(
                    'Stats Generation Error',
                    extra={
                        'stats': stats_info,
                        'error': str(e),
                        'error_type': type(e).__name__
                    },
                    exc_info=True
                )
                raise
                
        return wrapper
    return decorator

def log_export(func):
    """Dekorator do logowania eksportu danych."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = datetime.now()
        
        # Zbierz informacje o eksporcie
        export_info = {
            'args': args,
            'kwargs': kwargs,
            'timestamp': start_time.isoformat()
        }
        
        try:
            # Wykonaj funkcję
            result = func(*args, **kwargs)
            
            # Oblicz czas wykonania
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Zaloguj sukces
            logger.info(
                'Export Success',
                extra={
                    'export': export_info,
                    'execution_time': execution_time,
                    'file_size': len(result.get_data())
                }
            )
            
            return result
            
        except Exception as e:
            # Zaloguj błąd
            logger.error(
                'Export Error',
                extra={
                    'export': export_info,
                    'error': str(e),
                    'error_type': type(e).__name__
                },
                exc_info=True
            )
            raise
            
    return wrapper

def log_error(error: Exception, context: Optional[Dict[str, Any]] = None):
    """Funkcja do logowania błędów."""
    error_info = {
        'error_type': type(error).__name__,
        'error_message': str(error),
        'timestamp': datetime.now().isoformat()
    }
    
    if context:
        error_info['context'] = context
    
    if hasattr(error, 'details'):
        error_info['details'] = error.details
    
    logger.error(
        'Application Error',
        extra={'error': error_info},
        exc_info=True
    ) 