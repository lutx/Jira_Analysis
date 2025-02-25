import logging
from flask import current_app
import os
from logging.handlers import WatchedFileHandler
from pathlib import Path
import time
import sys

class AppLogger:
    @staticmethod
    def error(message: str, error: Exception = None):
        error_msg = f"{message}: {str(error)}" if error else message
        current_app.logger.error(error_msg)

    @staticmethod
    def warning(message: str):
        current_app.logger.warning(message)

    @staticmethod
    def info(message: str):
        current_app.logger.info(message)

logger = AppLogger()

def setup_logger(app):
    """Configure application logging."""
    if not app.debug:
        # Ensure logs directory exists
        log_dir = Path(app.instance_path) / 'logs'
        log_dir.mkdir(parents=True, exist_ok=True)
        
        log_file = log_dir / 'app.log'
        csrf_log = log_dir / 'csrf.log'
        
        # Configure main application logger
        try:
            # Use WatchedFileHandler instead of RotatingFileHandler
            file_handler = WatchedFileHandler(
                str(log_file),
                encoding='utf-8'
            )
            
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s %(levelname)s: %(message)s '
                '[in %(pathname)s:%(lineno)d]'
            ))
            
            file_handler.setLevel(logging.INFO)
            app.logger.addHandler(file_handler)
            
            # Always add a console handler for development
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(logging.Formatter(
                '%(asctime)s %(levelname)s: %(message)s'
            ))
            console_handler.setLevel(logging.INFO)
            app.logger.addHandler(console_handler)
            
        except Exception as e:
            # Fallback to console only logging
            app.logger.warning(
                f"Could not create log file handler: {str(e)}. Logging to console only."
            )
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(logging.Formatter(
                '%(asctime)s %(levelname)s: %(message)s'
            ))
            console_handler.setLevel(logging.INFO)
            app.logger.addHandler(console_handler)
        
        # Configure CSRF logging
        try:
            csrf_handler = WatchedFileHandler(
                str(csrf_log),
                encoding='utf-8'
            )
            csrf_handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            ))
            csrf_handler.setLevel(logging.DEBUG)
            
            csrf_logger = logging.getLogger('flask_wtf.csrf')
            csrf_logger.addHandler(csrf_handler)
            csrf_logger.setLevel(logging.DEBUG)
            
        except Exception as e:
            app.logger.warning(
                f"Could not create CSRF log handler: {str(e)}. CSRF logging disabled."
            )
    
    # Set root logger level
    app.logger.setLevel(logging.INFO)
    
    # Log startup message
    app.logger.info('Application startup - Logging system initialized')
    
    return app 