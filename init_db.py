import os
import shutil
import subprocess
import json
from pathlib import Path
from flask import current_app
from app import create_app, db
from flask_migrate import Migrate
from app.models import (
    User,
    Role,
    UserRole,
    Team,
    TeamMembership,
    Project,
    Portfolio,
    ProjectAssignment,
    Worklog,
    Setting,
    JiraConfig
)
from app.config import Config
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Zdefiniuj dostępne uprawnienia
PERMISSIONS = {
    'admin': [
        'Odczyt',
        'Zapis',
        'Usuwanie',
        'Administrator',
        'Zarządzanie zespołami',
        'Zarządzanie użytkownikami',
        'Zarządzanie projektami',
        'Zarządzanie worklogami',
        'Zarządzanie ustawieniami',
        'Podgląd raportów',
        'Zarządzanie raportami'
    ],
    'user': [
        'Odczyt',
        'Zapis',
        'Podgląd raportów'
    ]
}

def run_flask_command(command):
    """Run Flask command and return its output."""
    result = subprocess.run(
        f"flask {command}",
        shell=True,
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        print(f"Error running command 'flask {command}':")
        print(result.stderr)
        raise RuntimeError(f"Command 'flask {command}' failed")
    return result.stdout

def initialize_database():
    """Initialize the database with proper error handling."""
    try:
        app = create_app()
        
        # Get database path from config
        db_path = Path(app.config['SQLALCHEMY_DATABASE_URI'].split('///')[1].split('?')[0])
        logger.info(f"Database path: {db_path}")
        
        # Ensure database file exists and is writable
        if not db_path.exists():
            logger.info("Creating database file...")
            db_path.parent.mkdir(parents=True, exist_ok=True)
            db_path.touch(mode=0o666)
            logger.info("Database file created successfully")
        
        # Check file permissions
        if not os.access(db_path, os.W_OK):
            raise PermissionError(f"Cannot write to database file: {db_path}")
        
        with app.app_context():
            # Create all tables
            logger.info("Creating database tables...")
            db.create_all()
            logger.info("Database tables created successfully")
            
            # Test database connection
            result = db.session.execute('SELECT 1').scalar()
            logger.info(f"Database connection test successful: {result}")
            
            # Commit any pending transactions
            db.session.commit()
            
            return True
            
    except Exception as e:
        logger.error(f"Error initializing database: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    initialize_database() 