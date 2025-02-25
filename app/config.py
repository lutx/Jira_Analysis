import os
from datetime import timedelta
from dotenv import load_dotenv
from pathlib import Path

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(os.path.dirname(basedir), '.env'))

class Config:
    """Base configuration."""
    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key'
    
    # CSRF Protection
    WTF_CSRF_ENABLED = True
    WTF_CSRF_SECRET_KEY = os.environ.get('WTF_CSRF_SECRET_KEY') or 'csrf-secret-key'
    WTF_CSRF_TIME_LIMIT = 3600
    WTF_CSRF_SSL_STRICT = False
    WTF_CSRF_CHECK_DEFAULT = True
    WTF_CSRF_METHODS = ['POST', 'PUT', 'PATCH', 'DELETE']
    
    # Session Configuration
    SESSION_TYPE = 'filesystem'
    PERMANENT_SESSION_LIFETIME = timedelta(days=1)
    SESSION_COOKIE_NAME = 'session'
    SESSION_COOKIE_SECURE = False  # Set to True in production
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_REFRESH_EACH_REQUEST = True
    
    # Database
    basedir = Path(__file__).parent.parent
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        f'sqlite:///{basedir / "instance/app.db"}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # JIRA
    JIRA_URL = os.environ.get('JIRA_URL')
    JIRA_USERNAME = os.environ.get('JIRA_USERNAME')
    JIRA_API_TOKEN = os.environ.get('JIRA_API_TOKEN')
    JIRA_PROJECT_KEY = os.environ.get('JIRA_PROJECT_KEY')
    
    # JWT
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'jwt-secret-key-change-me')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    
    # Redis & Celery
    REDIS_URL = os.environ.get('REDIS_URL') or 'redis://localhost:6379/0'
    CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL') or REDIS_URL
    CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND') or REDIS_URL
    
    # Security
    CONTENT_SECURITY_POLICY = {
        'default-src': ["'self'"],
        'script-src': ["'self'", "'unsafe-inline'", "'unsafe-eval'"],
        'style-src': ["'self'", "'unsafe-inline'"],
        'img-src': ["'self'", "data:", "https:"],
        'connect-src': ["'self'", "https://jira-test.lbpro.pl", "http://localhost:5003"]
    }

    # Flask-Login config
    LOGIN_DISABLED = False
    LOGIN_VIEW = 'auth.login'
    LOGIN_MESSAGE = 'Please log in to access this page.'
    LOGIN_MESSAGE_CATEGORY = 'info'
    REMEMBER_COOKIE_DURATION = timedelta(days=30)
    REMEMBER_COOKIE_SECURE = False
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_REFRESH_EACH_REQUEST = True
    REMEMBER_COOKIE_NAME = 'remember_token'
    REMEMBER_COOKIE_DOMAIN = None
    REMEMBER_COOKIE_PATH = '/'
    SESSION_PROTECTION = 'strong'
    
    # Logging config
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = basedir / 'instance/logs/app.log'

    # JIRA settings - bez wartości domyślnych
    JIRA_TIMEOUT = int(os.environ.get('JIRA_TIMEOUT', '30'))
    VERIFY_SSL = os.environ.get('VERIFY_SSL', 'True').lower() == 'true'
    JIRA_ENABLED = os.environ.get('JIRA_ENABLED', 'True').lower() == 'true'

    # Flask-specific config
    STATIC_FOLDER = 'static'
    TEMPLATE_FOLDER = 'templates'

    URLLIB3_DISABLE_WARNINGS = True

    DEBUG = True
    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'verbose': {
                'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
            },
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'formatter': 'verbose',
                'level': 'DEBUG',
            },
            'file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': 'logs/app.log',
                'maxBytes': 1024 * 1024,  # 1 MB
                'backupCount': 3,
                'formatter': 'verbose',
                'level': 'DEBUG',
            },
        },
        'loggers': {
            'app': {
                'handlers': ['console', 'file'],
                'level': 'DEBUG',
            },
            'flask_wtf': {
                'handlers': ['console', 'file'],
                'level': 'DEBUG',
            },
        }
    }

    # CORS settings
    CORS_HEADERS = 'Content-Type'

    # Admin settings
    SUPERADMIN_EMAIL = os.environ.get('SUPERADMIN_EMAIL', 'admin@example.com')
    SUPERADMIN_PASSWORD = os.environ.get('SUPERADMIN_PASSWORD', 'admin123')

    # Session Configuration
    SESSION_TYPE = 'filesystem'
    SESSION_FILE_DIR = basedir / 'instance/flask_session'
    PERMANENT_SESSION_LIFETIME = 86400  # 24 hours
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_NAME = 'session'
    SESSION_REFRESH_EACH_REQUEST = True
    SESSION_COOKIE_DOMAIN = None
    SESSION_COOKIE_PATH = '/'
    
    # CSRF Protection
    WTF_CSRF_ENABLED = True
    WTF_CSRF_SECRET_KEY = os.environ.get('WTF_CSRF_SECRET_KEY') or 'csrf-secret-key'
    WTF_CSRF_TIME_LIMIT = 3600
    WTF_CSRF_SSL_STRICT = False
    WTF_CSRF_CHECK_DEFAULT = True
    WTF_CSRF_METHODS = ['POST', 'PUT', 'PATCH', 'DELETE']
    WTF_CSRF_HEADERS = ['X-CSRFToken', 'X-CSRF-Token']
    
    # Application Configuration
    SERVER_NAME = None
    APPLICATION_ROOT = '/'
    PREFERRED_URL_SCHEME = 'http'
    
    # CORS Configuration
    CORS_ORIGINS = ["http://192.168.90.114:5003"]  # Tylko ten host
    CORS_ALLOW_HEADERS = ['Content-Type', 'Authorization', 'X-CSRFToken']
    CORS_EXPOSE_HEADERS = ['Content-Range', 'X-Content-Range']
    CORS_METHODS = ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']
    CORS_SUPPORTS_CREDENTIALS = True

    # Cache settings
    CACHE_TYPE = 'simple'
    CACHE_DEFAULT_TIMEOUT = 300

    # Ensure instance directory exists
    @classmethod
    def init_app(cls, app):
        """Initialize application configuration."""
        instance_path = Path(app.instance_path)
        instance_path.mkdir(parents=True, exist_ok=True)
        
        # Create required directories
        (instance_path / 'logs').mkdir(exist_ok=True)
        (instance_path / 'flask_session').mkdir(exist_ok=True)
        
        # Ensure database directory exists
        db_path = Path(cls.SQLALCHEMY_DATABASE_URI.replace('sqlite:///', ''))
        db_path.parent.mkdir(parents=True, exist_ok=True)