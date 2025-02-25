import os
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

def configure_logging(app):
    """Configure logging for the application."""
    
    # Ensure logs directory exists
    log_dir = Path(app.root_path).parent / 'logs'
    log_dir.mkdir(exist_ok=True)
    
    # Configure main app logger
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # File handler for all logs
    file_handler = RotatingFileHandler(
        log_dir / 'app.log',
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)
    
    # Error file handler
    error_handler = RotatingFileHandler(
        log_dir / 'error.log',
        maxBytes=10 * 1024 * 1024,
        backupCount=5
    )
    error_handler.setFormatter(formatter)
    error_handler.setLevel(logging.ERROR)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.addHandler(file_handler)
    root_logger.addHandler(error_handler)
    
    # Set log level from config
    root_logger.setLevel(app.config.get('LOG_LEVEL', logging.INFO))
    
    # Special handling for development mode
    if app.debug:
        # Stream handler for console output
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(logging.DEBUG)
        root_logger.addHandler(console_handler) 