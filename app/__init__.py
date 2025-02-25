from flask import Flask, render_template, jsonify, request, redirect, url_for, session, flash, g
import logging
from pathlib import Path
from app.config import Config
from app.extensions import (
    init_extensions, 
    db, 
    migrate, 
    login_manager, 
    jwt,
    init_security_headers,
    csrf,
    cache,
    session
)
from app.utils.logger import setup_logger
from app.routes import register_blueprints
from app.cli import register_commands, init_app as init_cli
from app.utils.filters import register_filters, filters_bp
from app.errors.handlers import register_error_handlers
from app.models.user import User
from dotenv import load_dotenv
import os
from sqlalchemy.exc import OperationalError
from werkzeug.exceptions import HTTPException
from app.utils.env_checker import check_jira_env_vars
from app.commands.create_superadmin import create_superadmin_command
from app.utils.logger import setup_logger
from app.utils.template_helpers import get_menu_items
from celery import Celery
from sqlalchemy import inspect
from flask_wtf.csrf import CSRFError, generate_csrf
from flask_cors import CORS
import json
import uuid
from flask import g
from flask_login import current_user
from app.models.database import init_db
from datetime import timedelta
from app.exceptions import AppException, BaseAppException
from app.commands.db_commands import reset_db_command, init_db_command
from app.commands.check_admin import check_admin_command
from app.routes.api import api_bp
from logging.handlers import RotatingFileHandler
from app.routes.admin import admin_bp

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def create_app(config_object: str = "app.config.Config") -> Flask:
    """Application factory."""
    app = Flask(__name__,
                static_folder='static',
                template_folder='templates')
                
    # Load config
    app.config.from_object(config_object)
    
    # Initialize config
    if hasattr(app.config, 'init_app'):
        app.config.init_app(app)
    
    # Create required directories
    instance_path = Path(app.instance_path)
    instance_path.mkdir(parents=True, exist_ok=True)
    
    log_dir = instance_path / 'logs'
    session_dir = instance_path / 'flask_session'
    
    for directory in [log_dir, session_dir]:
        directory.mkdir(parents=True, exist_ok=True)
    
    # Initialize logging
    setup_logger(app)
    
    # Initialize CSRF protection first
    csrf.init_app(app)
    
    # Initialize all other extensions
    init_extensions(app)
    
    # Register blueprints
    from app.routes.main import main_bp
    from app.routes.auth import auth_bp
    from app.routes.admin import admin_bp
    from app.routes.api import api_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(filters_bp)
    
    # Register error handlers
    register_error_handlers(app)
    
    with app.app_context():
        # Initialize encryption key
        from app.utils.crypto import validate_encryption_key, get_encryption_key
        try:
            if not validate_encryption_key():
                logger.error("Encryption key validation failed - please check your ENCRYPTION_KEY environment variable")
                raise RuntimeError("Invalid encryption key - cannot start application")
        except Exception as e:
            logger.error(f"Error validating encryption key: {str(e)}")
            raise RuntimeError("Cannot start application due to encryption key error") from e
        
        # Create database tables
        try:
            db.create_all()
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Error creating database tables: {str(e)}")
            raise
            
        # Initialize JIRA configuration table
        try:
            from app.models.jira_config import JiraConfig
            inspector = inspect(db.engine)
            if not inspector.has_table(JiraConfig.__tablename__):
                JiraConfig.__table__.create(db.engine)
                logger.info(f"Created JIRA configuration table")
        except Exception as e:
            logger.error(f"Error creating JIRA configuration table: {str(e)}")
            raise
    
    @app.before_request
    def before_request():
        # Reduce logging verbosity for static files
        if not request.path.startswith('/static/'):
            logger.info(f"Processing request to {request.url}")
            logger.info(f"Request method: {request.method}")
            logger.info(f"Request headers: {dict(request.headers)}")
            
            # Bezpieczne logowanie danych sesji
            try:
                if hasattr(session, '_get_current_object'):
                    session_obj = session._get_current_object()
                    session_data = dict(session_obj) if session_obj else {}
                    logger.info(f"Session data: {session_data}")
            except Exception as e:
                logger.error(f"Error accessing session data: {str(e)}")
                
            logger.info(f"Cookie data: {request.cookies}")

    @app.after_request
    def after_request(response):
        origin = request.headers.get('Origin')
        if origin == "http://192.168.90.114:5003":
            response.headers['Access-Control-Allow-Origin'] = origin
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-CSRFToken'
            response.headers['Vary'] = 'Origin'
        
        # Ensure CSRF token is set in response headers
        if not request.path.startswith('/static/'):
            response.headers.set('X-CSRF-Token', generate_csrf())
        
        # Upewnij się, że ciasteczka sesji są poprawnie ustawione
        try:
            if hasattr(session, 'sid'):
                response.set_cookie(
                    'session',
                    session.sid,
                    httponly=True,
                    secure=False,  # Zmień na True w produkcji
                    samesite='Lax',
                    domain=None,
                    path='/'
                )
        except Exception as e:
            logger.error(f"Error setting session cookie: {str(e)}")
        
        # Reduce logging verbosity for static files
        if not request.path.startswith('/static/'):
            logger.info(f"Response status: {response.status_code}")
            logger.info(f"Response headers: {dict(response.headers)}")
        return response
    
    # Configure login manager
    @login_manager.user_loader
    def load_user(user_id):
        try:
            return User.query.get(int(user_id))
        except Exception as e:
            app.logger.error(f"Error loading user: {str(e)}")
            return None
    
    # Set login view and messages
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
    # Attach the login_manager to app so it can be accessed via current_app
    app.login_manager = login_manager
    
    return app

def register_error_handlers(app):
    """Register error handlers."""
    
    @app.errorhandler(Exception)
    def handle_exception(e):
        """Handle all unhandled exceptions."""
        if isinstance(e, HTTPException):
            return handle_http_error(e)
            
        logger.error(f"Unhandled exception: {str(e)}", exc_info=True)
        return render_template('errors/500.html'), 500

    @app.errorhandler(HTTPException)
    def handle_http_error(error):
        """Handle HTTP exceptions."""
        if request.is_json:
            return jsonify({
                'error': error.name.lower(),
                'message': str(error)
            }), error.code
            
        return render_template(f'errors/{error.code}.html'), error.code

    @app.errorhandler(AppException)
    def handle_app_exception(error):
        """Handle application-specific exceptions."""
        if request.is_json:
            return jsonify(error.to_dict()), error.code
            
        flash(str(error), 'error')
        return render_template('errors/error.html', error=error), error.code

    @app.errorhandler(404)
    def not_found_error(error):
        if request.is_json:
            return jsonify({
                'error': 'not_found',
                'message': 'Resource not found'
            }), 404
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        logger.error(f'Server Error: {error}', exc_info=True)
        if request.is_json:
            return jsonify({
                'error': 'internal_server_error',
                'message': 'An unexpected error occurred'
            }), 500
        return render_template('errors/500.html'), 500

    @app.errorhandler(403)
    def forbidden_error(error):
        if request.is_json:
            return jsonify({
                'error': 'forbidden',
                'message': 'Access denied'
            }), 403
        flash('Nie masz uprawnień do tej strony.', 'danger')
        return render_template('errors/403.html'), 403

def init_settings(app):
    """Initialize application settings."""
    try:
        from app.models.setting import Setting
        
        # Default settings
        default_settings = {
            'SYNC_INTERVAL': 3600,
            'LOG_LEVEL': 'INFO',
            'CACHE_TIMEOUT': 300
        }
        
        # Add settings if they don't exist
        with app.app_context():
            try:
                # Sprawdź czy tabela istnieje
                Setting.query.first()
                
                # Dodaj domyślne ustawienia
                for key, value in default_settings.items():
                    if not Setting.get_value(key):
                        Setting.set_value(key, value)
                        logger.info(f"Added default setting: {key}={value}")
                        
            except OperationalError:
                logger.warning("Settings table does not exist yet - skipping initialization")
                
    except Exception as e:
        logger.error(f"Error initializing settings: {str(e)}")

def init_jira_config(app):
    """Initialize JIRA configuration."""
    try:
        from app.models.jira_config import JiraConfig
        
        inspector = inspect(db.engine)
        if 'jira_config' not in inspector.get_table_names():
            logger.warning("JIRA config table does not exist yet - skipping initialization")
            return
            
        config = JiraConfig.query.filter_by(is_active=True).first()
        if config:
            app.config.update({
                'JIRA_URL': config.url,
                'JIRA_USERNAME': config.username,
                'JIRA_API_TOKEN': config.api_token,
                'JIRA_ENABLED': True
            })
            logger.info("=== JIRA Config Values ===")
            logger.info(f"URL: {config.url}")
            logger.info(f"Username: {config.username}")
            logger.info(f"API Token exists: {bool(config.api_token)}")
        else:
            logger.warning("No active JIRA configuration found")
                
    except Exception as e:
        logger.error(f"Error initializing JIRA config: {str(e)}")
        raise

def register_commands(app):
    """Register CLI commands."""
    from app.commands.create_superadmin import create_superadmin_command
    from app.commands.check_admin import check_admin_command
    from app.commands.update_db import update_db_command
    
    app.cli.add_command(create_superadmin_command)
    app.cli.add_command(check_admin_command)
    app.cli.add_command(update_db_command)

def create_celery_app(app):
    celery = Celery(
        app.import_name,
        broker=app.config['CELERY_BROKER_URL']
    )
    celery.conf.update(app.config)
    return celery