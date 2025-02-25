import click
from flask.cli import with_appcontext
from app.extensions import db
from app.models import Role, User
import logging
from app.models.role import Role

logger = logging.getLogger(__name__)

@click.command('init-db')
@with_appcontext
def init_db_command():
    """Initialize database with default data."""
    try:
        # Create tables
        db.create_all()
        
        # Create default roles with proper permissions
        default_roles = [
            {
                'name': 'user',
                'description': 'Basic user role',
                'permissions': ['read', 'write', 'view_reports']
            },
            {
                'name': 'admin',
                'description': 'Administrator role',
                'permissions': [
                    'read', 'write', 'delete', 'admin',
                    'manage_teams', 'manage_users', 'manage_projects',
                    'manage_worklogs', 'view_reports'
                ]
            },
            {
                'name': 'superadmin',
                'description': 'Super Administrator role',
                'permissions': Role.PERMISSIONS.keys()  # All available permissions
            }
        ]
        
        for role_data in default_roles:
            existing_role = Role.query.filter_by(name=role_data['name']).first()
            if not existing_role:
                role = Role(**role_data)
                db.session.add(role)
                click.echo(f"Created role: {role_data['name']}")
        
        db.session.commit()
        click.echo("Database initialized successfully")
        
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        db.session.rollback()
        raise 