from .base import Config
import logging
import os

class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    TESTING = False
    SQLALCHEMY_ECHO = False
    
    LOG_LEVEL = logging.INFO
    
    # Cache settings
    CACHE_TYPE = 'redis'
    CACHE_REDIS_URL = os.environ.get('REDIS_URL')
    CACHE_DEFAULT_TIMEOUT = 3600
    
    # Security settings
    WTF_CSRF_ENABLED = True
    WTF_CSRF_SSL_STRICT = True
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Production-specific settings
    PREFERRED_URL_SCHEME = 'https' 