import os
from datetime import timedelta
from pathlib import Path
from cryptography.fernet import Fernet
from dotenv import load_dotenv
import logging

# Load .env file
load_dotenv()

logger = logging.getLogger(__name__)

basedir = Path(__file__).parent

class Config:
    # Get absolute paths
    BASE_DIR = Path(__file__).resolve().parent.parent
    INSTANCE_PATH = BASE_DIR / 'instance'
    DB_PATH = INSTANCE_PATH / 'app.db'
    
    # Ensure instance directory exists
    INSTANCE_PATH.mkdir(parents=True, exist_ok=True)
    
    # Database configuration
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{DB_PATH.as_posix()}?check_same_thread=False'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Konfiguracja SQLAlchemy
    SQLALCHEMY_ENGINE_OPTIONS = {
        'connect_args': {
            'timeout': 15
        }
    }

    # Inne ustawienia...
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'dev-key-change-me')
    DEBUG = True
    
    # Ensure instance path exists and is writable
    if not os.access(INSTANCE_PATH, os.W_OK):
        raise RuntimeError(f"Instance path {INSTANCE_PATH} is not writable")
    
    # Session config
    SESSION_TYPE = 'filesystem'
    SESSION_FILE_DIR = 'instance/flask_session'
    PERMANENT_SESSION_LIFETIME = timedelta(days=31)
    
    # Security
    WTF_CSRF_ENABLED = True
    
    # Logging
    LOG_TO_STDOUT = os.environ.get('LOG_TO_STDOUT')
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    
    # Debug settings
    TESTING = False
    
    # Server settings
    PORT = int(os.environ.get('PORT', 5003))
    HOST = os.environ.get('HOST', '0.0.0.0')
    
    # Session settings
    SESSION_FILE_THRESHOLD = 500  # Maksymalna liczba plików sesji
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # CSRF protection
    WTF_CSRF_SECRET_KEY = os.environ.get('WTF_CSRF_SECRET_KEY', 'your-csrf-secret-key')
    WTF_CSRF_TIME_LIMIT = None  # Token nie wygasa
    
    # Jira settings
    JIRA_URL = os.environ.get('JIRA_URL')
    JIRA_USERNAME = os.environ.get('JIRA_USERNAME')
    JIRA_API_TOKEN = os.environ.get('JIRA_API_TOKEN')
    JIRA_TIMEOUT = int(os.getenv('JIRA_TIMEOUT', 30))
    VERIFY_SSL = os.getenv('VERIFY_SSL', 'True').lower() == 'true'
    JIRA_ENABLED = os.environ.get('JIRA_ENABLED', 'False').lower() == 'true'
    JIRA_BASE_URL = os.environ.get('JIRA_BASE_URL')
    
    # Dodajmy zmienną do kontroli czy wymagać połączenia z Jirą przy logowaniu
    REQUIRE_JIRA_AUTH = False  # W trybie development nie wymagamy połączenia z Jirą
    
    # Admin settings - moved from environment variables to default values
    SUPERADMIN_EMAIL = os.environ.get('SUPERADMIN_EMAIL', 'admin@example.com')
    SUPERADMIN_PASSWORD = os.environ.get('SUPERADMIN_PASSWORD', 'admin123')
    
    # Database settings
    SQLALCHEMY_ECHO = True
    
    # Generowanie klucza szyfrowania jeśli nie istnieje
    ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY')
    if not ENCRYPTION_KEY:
        ENCRYPTION_KEY = Fernet.generate_key().decode()
        os.environ['ENCRYPTION_KEY'] = ENCRYPTION_KEY

    # Cache settings
    CACHE_TYPE = 'simple'
    CACHE_DEFAULT_TIMEOUT = 300
    CACHE_THRESHOLD = 1000  # Maksymalna liczba elementów w cache

    # Flask-Login config
    SESSION_PROTECTION = 'strong'
    REMEMBER_COOKIE_DURATION = timedelta(days=14)
    REMEMBER_COOKIE_SECURE = False  # Set to True in production
    REMEMBER_COOKIE_HTTPONLY = True
    
    # Content Security Policy
    CONTENT_SECURITY_POLICY = {
        'default-src': ["'self'"],
        'script-src': [
            "'self'",
            'https://code.jquery.com',
            'https://cdn.jsdelivr.net',
            'https://cdnjs.cloudflare.com',
            "'unsafe-inline'",
            "'unsafe-eval'"
        ],
        'style-src': [
            "'self'",
            'https://cdn.jsdelivr.net',
            'https://cdnjs.cloudflare.com',
            "'unsafe-inline'"
        ],
        'font-src': [
            "'self'",
            'https://cdnjs.cloudflare.com',
            'https://cdn.jsdelivr.net'
        ],
        'img-src': [
            "'self'",
            'data:',
            'https:'
        ],
        'connect-src': [
            "'self'"
        ],
        'script-src-elem': [
            "'self'",
            'https://code.jquery.com',
            'https://cdn.jsdelivr.net',
            'https://cdnjs.cloudflare.com',
            "'unsafe-inline'",
            "'unsafe-eval'",
            '!https://kit.fontawesome.com'
        ]
    }

    # Flask-Migrate settings
    MIGRATION_DIR = Path(basedir, 'migrations')

    # JWT settings
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'your-jwt-secret-key')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)

    @staticmethod
    def log_config():
        """Log configuration settings."""
        logger.info("=== Configuration ===")
        logger.info(f"JIRA_URL: {Config.JIRA_URL}")
        logger.info(f"JIRA_USERNAME: {Config.JIRA_USERNAME}")
        logger.info(f"JIRA_API_TOKEN exists: {bool(Config.JIRA_API_TOKEN)}")
        logger.info(f"JIRA_ENABLED: {Config.JIRA_ENABLED}")
        logger.info("===================")

class DevelopmentConfig(Config):
    DEBUG = True
    WTF_CSRF_ENABLED = True

class ProductionConfig(Config):
    DEBUG = False
    WTF_CSRF_ENABLED = True

class TestingConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
    DATABASE = ':memory:'

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
} 