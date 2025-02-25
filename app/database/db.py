from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask import current_app
import logging

logger = logging.getLogger(__name__)

db = SQLAlchemy()
migrate = Migrate()

def init_app(app):
    """Initialize database with Flask app"""
    db.init_app(app)
    app.teardown_appcontext(close_db)
    with app.app_context():
        db.create_all()

def get_db():
    """Get database session"""
    return db.session

def close_db(e=None):
    """Close database session"""
    db.session.remove()

def init_db(app):
    """Initialize database with app context."""
    try:
        db.init_app(app)
        migrate.init_app(app, db)
        
        with app.app_context():
            # Create all tables
            db.create_all()
            
        logger.info("Database initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"Database initialization error: {str(e)}")
        return False 