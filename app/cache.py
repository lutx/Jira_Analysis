from typing import Any, Optional, Callable
from datetime import datetime, timedelta
import hashlib
import json
import logging
from functools import wraps
from flask_caching import Cache

logger = logging.getLogger(__name__)
cache = Cache()

def init_cache(app):
    """Inicjalizuje cache dla aplikacji."""
    cache_config = {
        'CACHE_TYPE': app.config.get('CACHE_TYPE', 'simple'),
        'CACHE_DEFAULT_TIMEOUT': app.config.get('CACHE_TIMEOUT', 300),
        'CACHE_KEY_PREFIX': app.config.get('CACHE_PREFIX', 'team_stats_'),
        'CACHE_THRESHOLD': app.config.get('CACHE_MAX_ITEMS', 1000)
    }
    cache.init_app(app, config=cache_config)

def generate_cache_key(*args, **kwargs) -> str:
    """Generuje klucz cache'u na podstawie argumentów."""
    key_parts = [str(arg) for arg in args]
    key_parts.extend(f"{k}:{v}" for k, v in sorted(kwargs.items()))
    
    key_string = "|".join(key_parts)
    return hashlib.md5(key_string.encode()).hexdigest()

def cache_stats(timeout: Optional[int] = None):
    """Dekorator do cache'owania wyników funkcji statystyk."""
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def wrapper(*args, **kwargs):
            # Generuj klucz cache'u
            cache_key = generate_cache_key(
                f.__name__,
                *args,
                **kwargs
            )
            
            # Spróbuj pobrać z cache'u
            result = cache.get(cache_key)
            if result is not None:
                logger.debug(f"Cache hit for {cache_key}")
                return result
            
            # Wykonaj funkcję i zapisz wynik w cache'u
            result = f(*args, **kwargs)
            cache.set(cache_key, result, timeout=timeout)
            logger.debug(f"Cache miss for {cache_key}")
            
            return result
        return wrapper
    return decorator

def invalidate_team_cache(team_id: int) -> None:
    """Unieważnia cache dla danego zespołu."""
    pattern = f"team_{team_id}_*"
    cache.delete_many(pattern)
    logger.info(f"Invalidated cache for team {team_id}")

def clear_expired_cache() -> None:
    """Czyści wygasłe wpisy z cache'u."""
    if hasattr(cache, 'clear_expired'):
        cache.clear_expired()
        logger.info("Cleared expired cache entries")

class CacheManager:
    """Klasa do zarządzania cache'm."""
    
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Inicjalizuje manager cache'u dla aplikacji."""
        self.app = app
        init_cache(app)
        
        # Dodaj zadanie czyszczenia cache'u do harmonogramu
        if app.config.get('CACHE_CLEANUP_ENABLED', True):
            self.schedule_cache_cleanup()
    
    def schedule_cache_cleanup(self):
        """Planuje regularne czyszczenie cache'u."""
        from apscheduler.schedulers.background import BackgroundScheduler
        scheduler = BackgroundScheduler()
        
        interval = self.app.config.get('CACHE_CLEANUP_INTERVAL', 3600)  # domyślnie co godzinę
        scheduler.add_job(
            clear_expired_cache,
            'interval',
            seconds=interval,
            id='cache_cleanup'
        )
        scheduler.start()
    
    def get_cache_stats(self) -> dict:
        """Zwraca statystyki cache'u."""
        return {
            'size': len(cache.cache._cache),
            'hits': cache.cache.hits,
            'misses': cache.cache.misses,
            'maxsize': cache.cache.maxsize,
            'currsize': cache.cache.currsize
        } 