from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event, inspect
from flask import current_app
import logging
from app.extensions import db
from app.models import User, Role

logger = logging.getLogger(__name__)

def init_db(app):
    """Initialize the database."""
    try:
        db.create_all()
        
        # Dodaj podstawowe role jeśli nie istnieją
        from app.models.role import Role
        
        default_roles = [
            {'name': 'superadmin', 'description': 'Pełne uprawnienia administracyjne'},
            {'name': 'admin', 'description': 'Uprawnienia administracyjne'},
            {'name': 'user', 'description': 'Podstawowe uprawnienia użytkownika'}
        ]
        
        for role_data in default_roles:
            if not Role.query.filter_by(name=role_data['name']).first():
                role = Role(**role_data)
                db.session.add(role)
                
        db.session.commit()
        logger.info("Database initialized successfully")
        
    except Exception as e:
        logger.error(f"Database initialization error: {str(e)}")
        raise

def init_db_old():
    """Initialize database tables."""
    try:
        # Import models
        from app.models.user import User
        from app.models.role import Role
        from app.models.team import Team
        from app.models.project import Project
        from app.models.worklog import Worklog
        from app.models.issue import Issue
        
        # Create default roles if they don't exist
        default_roles = [
            {
                'name': 'user',
                'description': 'Podstawowa rola użytkownika',
                'permissions': ['read']
            },
            {
                'name': 'admin',
                'description': 'Administrator',
                'permissions': ['read', 'write', 'admin']
            },
            {
                'name': 'superadmin',
                'description': 'Super Administrator',
                'permissions': [
                    'read', 'write', 'delete', 'admin',
                    'manage_teams', 'manage_users', 'manage_projects',
                    'manage_worklogs', 'manage_settings', 'view_reports',
                    'manage_reports'
                ]
            }
        ]
        
        # Create roles
        for role_data in default_roles:
            try:
                existing_role = Role.query.filter_by(name=role_data['name']).first()
                if not existing_role:
                    role = Role(**role_data)
                    db.session.add(role)
                    logger.info(f"Created role: {role_data['name']}")
            except Exception as e:
                logger.error(f"Error creating role {role_data['name']}: {str(e)}")
                continue
        
        try:
            db.session.commit()
            logger.info("Default roles created successfully")
        except Exception as e:
            logger.error(f"Error committing roles: {str(e)}")
            db.session.rollback()
            raise
        
    except Exception as e:
        logger.error(f"Error in init_db: {str(e)}")
        db.session.rollback()
        raise 