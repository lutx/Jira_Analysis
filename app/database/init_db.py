import sqlite3
import click
from flask import current_app
from flask.cli import with_appcontext
import logging
from app.extensions import db
from app.database.models import User, Role
from werkzeug.security import generate_password_hash

logger = logging.getLogger(__name__)

def init_db():
    """Initialize the database."""
    try:
        # Create all tables
        db.create_all()
        
        # Create default roles if they don't exist
        default_roles = ['admin', 'user', 'manager']
        for role_name in default_roles:
            if not Role.query.filter_by(name=role_name).first():
                role = Role(name=role_name)
                db.session.add(role)
        
        # Create superadmin if doesn't exist
        superadmin_email = current_app.config.get('SUPERADMIN_EMAIL')
        if superadmin_email and not User.query.filter_by(email=superadmin_email).first():
            superadmin = User(
                email=superadmin_email,
                username=superadmin_email,
                display_name='Super Administrator',
                is_active=True
            )
            superadmin.set_password(current_app.config.get('SUPERADMIN_PASSWORD'))
            
            admin_role = Role.query.filter_by(name='admin').first()
            if admin_role:
                superadmin.roles.append(admin_role)
            
            db.session.add(superadmin)
        
        db.session.commit()
        logger.info("Database initialized successfully")
        
    except Exception as e:
        logger.error(f"Database initialization error: {str(e)}")
        db.session.rollback()
        raise

@click.command('init-db')
@with_appcontext
def init_db_command():
    """Clear existing data and create new tables."""
    init_db()
    click.echo('Database initialized successfully')

def get_db():
    """Get database connection."""
    db = sqlite3.connect(
        current_app.config['DATABASE'],
        detect_types=sqlite3.PARSE_DECLTYPES
    )
    db.row_factory = sqlite3.Row
    return db 