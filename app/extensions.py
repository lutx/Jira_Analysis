from typing import Optional, Dict, Any
import jwt
from datetime import datetime, timedelta
from flask import current_app, session, make_response
from flask_wtf.csrf import CSRFProtect
from flask_caching import Cache
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import logging
import logging.handlers
import os
from jwt import ExpiredSignatureError, InvalidTokenError
from flask_login import LoginManager
from flask_session import Session
from pathlib import Path
from functools import wraps

logger = logging.getLogger(__name__)

# Single source of truth for all extensions
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()
jwt = JWTManager()
cache = Cache()
session = Session()  # Inicjalizacja sesji

# Export JWT errors
ExpiredSignatureError = ExpiredSignatureError
InvalidTokenError = InvalidTokenError

# Export other components
__all__ = ['db', 'jwt']

def init_logging(app):
    """Initialize logging configuration."""
    log_dir = Path(app.instance_path) / 'logs'
    log_dir.mkdir(exist_ok=True)
    
    # Configure file handlers with Windows-compatible settings
    file_handler = logging.handlers.RotatingFileHandler(
        filename=log_dir / 'app.log',
        maxBytes=10485760,  # 10MB
        backupCount=10,
        delay=True  # Don't open the file until first write
    )
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s '
        '[in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    
    # Configure error log with Windows-compatible settings
    error_handler = logging.handlers.RotatingFileHandler(
        filename=log_dir / 'error.log',
        maxBytes=10485760,  # 10MB
        backupCount=10,
        delay=True  # Don't open the file until first write
    )
    error_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s '
        '[in %(pathname)s:%(lineno)d]'
    ))
    error_handler.setLevel(logging.ERROR)
    
    # Configure console handler for development
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s '
        '[in %(pathname)s:%(lineno)d]'
    ))
    console_handler.setLevel(logging.DEBUG if app.debug else logging.INFO)
    
    # Remove any existing handlers to avoid duplicates
    for handler in app.logger.handlers[:]:
        app.logger.removeHandler(handler)
    
    # Add handlers to app logger
    app.logger.addHandler(file_handler)
    app.logger.addHandler(error_handler)
    app.logger.addHandler(console_handler)
    app.logger.setLevel(logging.DEBUG if app.debug else logging.INFO)
    
    # Configure root logger
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(error_handler)
    root_logger.addHandler(console_handler)
    root_logger.setLevel(logging.DEBUG if app.debug else logging.INFO)
    
    # Log startup message
    app.logger.info('Application logging initialized')

def add_security_headers(response):
    """Add security headers to response."""
    if not hasattr(current_app, 'config') or 'CONTENT_SECURITY_POLICY' not in current_app.config:
        return response
        
    try:
        csp = '; '.join([
            f"{key} {' '.join(values)}"
            for key, values in current_app.config['CONTENT_SECURITY_POLICY'].items()
        ])
        response.headers['Content-Security-Policy'] = csp
    except Exception as e:
        logger.error(f"Error adding security headers: {str(e)}")
    return response

def init_security_headers(app):
    """Initialize security headers."""
    @app.after_request
    def add_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        return response

def init_extensions(app):
    """Initialize Flask extensions."""
    # Initialize SQLAlchemy first
    db.init_app(app)
    
    # Initialize other extensions
    migrate.init_app(app, db)
    csrf.init_app(app)
    login_manager.init_app(app)
    jwt.init_app(app)
    cache.init_app(app)
    
    # Configure login manager
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
    # Initialize session in application context
    with app.app_context():
        session.init_app(app)
        
        # Create database tables if they don't exist
        try:
            db.create_all()
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Error creating database tables: {str(e)}")
            raise

    @login_manager.user_loader
    def load_user(user_id):
        from app.models.user import User
        try:
            return User.query.get(int(user_id))
        except Exception as e:
            logger.error(f"Error loading user: {str(e)}")
            return None

    @jwt.user_lookup_loader
    def user_lookup_callback(_jwt_header, jwt_data):
        from app.models import User
        identity = jwt_data["sub"]
        return User.query.filter_by(username=identity).first()

    @jwt.token_in_blocklist_loader
    def check_if_token_is_revoked(jwt_header, jwt_payload):
        from app.models import TokenBlocklist
        jti = jwt_payload["jti"]
        return TokenBlocklist.query.filter_by(jti=jti).first() is not None