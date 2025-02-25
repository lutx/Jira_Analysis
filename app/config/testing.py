from .base import Config
import logging
import os
from pathlib import Path

class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    DEBUG = True
    SQLALCHEMY_ECHO = True
    DATABASE = os.path.join(Path(__file__).parent.parent.parent, 'instance', 'test.db')
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{DATABASE}"
    LOG_LEVEL = logging.DEBUG
    CACHE_TYPE = 'null'
    
    # Wyłącz limity dla testów
    MAX_DATE_RANGE_DAYS = None
    MAX_EXPORT_SIZE = None 