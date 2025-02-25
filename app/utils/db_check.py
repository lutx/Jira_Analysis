import os
from pathlib import Path
from flask import current_app
import logging

logger = logging.getLogger(__name__)

def verify_db_config():
    """Verify database configuration."""
    try:
        # Check if SQLALCHEMY_DATABASE_URI is set
        db_uri = current_app.config.get('SQLALCHEMY_DATABASE_URI')
        if not db_uri:
            raise ValueError("SQLALCHEMY_DATABASE_URI is not set")
            
        # Check if database path exists
        db_path = Path(current_app.instance_path) / 'app.db'
        if not db_path.parent.exists():
            db_path.parent.mkdir(parents=True)
            logger.info(f"Created database directory: {db_path.parent}")
            
        # Create empty database file if it doesn't exist
        if not db_path.exists():
            db_path.touch()
            logger.info(f"Created database file: {db_path}")
            
        return True
        
    except Exception as e:
        logger.error(f"Database configuration error: {str(e)}", exc_info=True)
        return False 