import os
from pathlib import Path
from dotenv import load_dotenv
import logging
from datetime import timedelta

# Get absolute paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
INSTANCE_DIR = BASE_DIR / 'instance'
DB_PATH = INSTANCE_DIR / 'app.db'

# Ensure instance directory exists
INSTANCE_DIR.mkdir(parents=True, exist_ok=True)

class Config:
    """Base configuration."""
    
    # Paths
    BASE_DIR = str(BASE_DIR)
    INSTANCE_PATH = str(INSTANCE_DIR)
    
    # Database - upewnijmy się, że ścieżka jest absolutna i w formacie SQLAlchemy
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{DB_PATH.absolute()}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = True
    
    # SQLite specific settings
    SQLALCHEMY_ENGINE_OPTIONS = {
        'connect_args': {
            'check_same_thread': False,
            'timeout': 30
        }
    }
    
    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY', os.urandom(32))
    DEBUG = False
    TESTING = False
    
    # Session/CSRF
    SESSION_TYPE = 'filesystem'
    SESSION_FILE_DIR = str(INSTANCE_DIR / 'flask_session')
    PERMANENT_SESSION_LIFETIME = timedelta(days=1)
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # CSRF
    WTF_CSRF_ENABLED = True
    WTF_CSRF_SECRET_KEY = os.environ.get('WTF_CSRF_SECRET_KEY', os.urandom(32))
    WTF_CSRF_TIME_LIMIT = 3600
    WTF_CSRF_SSL_STRICT = False
    
    @staticmethod
    def init_app(app):
        """Initialize application configuration."""
        # Create required directories
        os.makedirs(app.instance_path, exist_ok=True)
        os.makedirs(os.path.join(app.instance_path, 'flask_session'), exist_ok=True)
        
        # Create database directory if it doesn't exist
        db_dir = os.path.dirname(DB_PATH)
        os.makedirs(db_dir, exist_ok=True)
        
        # Create empty database file if it doesn't exist
        if not os.path.exists(DB_PATH):
            with open(DB_PATH, 'a') as f:
                pass
            os.chmod(DB_PATH, 0o666)
    
    # Other settings...
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'dev-jwt-key'
    
    # JIRA settings
    JIRA_URL = os.environ.get('JIRA_URL')
    JIRA_USERNAME = os.environ.get('JIRA_USERNAME')
    JIRA_API_TOKEN = os.environ.get('JIRA_API_TOKEN')
    VERIFY_SSL = os.environ.get('VERIFY_SSL', 'True').lower() == 'true'
    
    # Podstawowa konfiguracja
    BASE_DIR = Path(__file__).parent.parent.parent
    
    # Admin settings
    SUPERADMIN_EMAIL = os.getenv('SUPERADMIN_EMAIL', 'admin@example.com')
    SUPERADMIN_PASSWORD = os.getenv('SUPERADMIN_PASSWORD', 'admin123')
    SUPERADMIN_USERNAME = os.getenv('SUPERADMIN_USERNAME', 'admin')
    
    # Debug settings
    FLASK_DEBUG = False  # Zamiast FLASK_ENV
    LOG_LEVEL = logging.INFO
    
    # Server settings
    PORT = 5003
    HOST = '0.0.0.0'
    
    # Upload settings
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'pdf', 'txt'}
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    
    # JWT settings
    JWT_ACCESS_TOKEN_EXPIRES = 24 * 60 * 60  # 24h
    JWT_REFRESH_TOKEN_EXPIRES = 30 * 24 * 60 * 60  # 30 days
    JWT_TOKEN_LOCATION = ['headers']
    JWT_HEADER_NAME = 'Authorization'
    JWT_HEADER_TYPE = 'Bearer'
    
    # CORS settings
    CORS_ORIGINS = ["http://localhost:5003"]
    CORS_METHODS = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    CORS_HEADERS = ["Content-Type", "Authorization", "X-Requested-With"]
    CORS_SUPPORTS_CREDENTIALS = True
    CORS_EXPOSE_HEADERS = ["Authorization"]
    
    # API settings
    API_TITLE = 'Jira Analysis API'
    API_VERSION = 'v1'
    OPENAPI_VERSION = '3.0.2'
    OPENAPI_URL_PREFIX = '/api/docs'
    OPENAPI_SWAGGER_UI_PATH = '/swagger'
    
    # Cache settings
    CACHE_TYPE = 'simple'
    CACHE_DEFAULT_TIMEOUT = 300
    
    # Security settings
    WTF_CSRF_ENABLED = True
    WTF_CSRF_SECRET_KEY = os.environ.get('WTF_CSRF_SECRET_KEY', 'csrf-key-change-in-production')
    WTF_CSRF_TIME_LIMIT = 3600  # 1 godzina
    
    # Static files
    STATIC_FOLDER = 'static'
    TEMPLATES_FOLDER = 'templates'
    
    # Timeouts
    REQUEST_TIMEOUT = 30
    JIRA_TIMEOUT = 10

    # Konfiguracja logowania
    LOG_LEVEL = logging.INFO
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    LOG_FILE = 'team_stats.log'
    LOG_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
    LOG_BACKUP_COUNT = 5
    
    # Konfiguracja cache'u
    CACHE_KEY_PREFIX = 'team_stats_'
    CACHE_THRESHOLD = 1000
    
    # Konfiguracja eksportu
    EXPORT_FORMATS = ['csv', 'pdf']
    WKHTMLTOPDF_PATH = os.environ.get('WKHTMLTOPDF_PATH', '/usr/local/bin/wkhtmltopdf')
    
    # Limity
    MAX_DATE_RANGE_DAYS = 365
    MAX_EXPORT_SIZE = 50 * 1024 * 1024  # 50 MB
    
    # Monitorowanie
    MONITORING_ENABLED = True
    SLOW_QUERY_THRESHOLD = 1.0  # sekundy
    
    # ... (reszta bazowej konfiguracji z obecnego config.py)

    @staticmethod
    def init_app(app):
        os.makedirs(app.instance_path, exist_ok=True) 