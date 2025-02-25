import os
from pathlib import Path
from flask import current_app
from app.database import get_db, init_db
import logging

logger = logging.getLogger(__name__)

def setup_database(env='development'):
    """Setup database for specific environment."""
    try:
        # Ensure instance directory exists
        instance_dir = Path(current_app.instance_path)
        instance_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        init_db()
        
        logger.info(f"Database setup completed for {env} environment")
        return True
        
    except Exception as e:
        logger.error(f"Database setup failed: {str(e)}")
        return False

def cleanup_databases():
    """Remove all database files."""
    try:
        instance_dir = Path(current_app.instance_path)
        for db_file in instance_dir.glob('*.db'):
            db_file.unlink()
        logger.info("All database files removed")
        return True
    except Exception as e:
        logger.error(f"Database cleanup failed: {str(e)}")
        return False 