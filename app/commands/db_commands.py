import click
from flask.cli import with_appcontext
from app.extensions import db
import logging
import os
from app.models import User, Role

logger = logging.getLogger(__name__)

@click.command('init-db')
@with_appcontext
def init_db_command():
    """Initialize the database."""
    try:
        # Create all tables
        db.create_all()
        
        # Create default roles if they don't exist
        roles = ['admin', 'user', 'manager']
        for role_name in roles:
            if not Role.query.filter_by(name=role_name).first():
                role = Role(name=role_name)
                db.session.add(role)
        
        db.session.commit()
        click.echo('Database initialized successfully.')
        
    except Exception as e:
        logger.error(f"Database initialization error: {str(e)}")
        db.session.rollback()
        click.echo(f'Error initializing database: {str(e)}')

@click.command('reset-db')
@with_appcontext
def reset_db_command():
    """Reset the database."""
    if os.path.exists('instance/app.db'):
        os.remove('instance/app.db')
    db.create_all()
    click.echo('Database reset successfully.')

def register_commands(app):
    app.cli.add_command(init_db_command)
    app.cli.add_command(reset_db_command) 