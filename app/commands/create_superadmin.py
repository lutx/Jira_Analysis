import click
from flask.cli import with_appcontext
from app.extensions import db
from app.models import User, Role
import logging

logger = logging.getLogger(__name__)

@click.command('create-superadmin')
@with_appcontext
def create_superadmin_command():
    """Create superadmin user."""
    try:
        # Check if superadmin already exists
        if User.query.filter_by(username='admin').first():
            click.echo('Superadmin already exists')
            return

        # Create superadmin role if it doesn't exist
        superadmin_role = Role.query.filter_by(name='superadmin').first()
        if not superadmin_role:
            superadmin_role = Role(
                name='superadmin',
                description='Super Administrator',
                permissions=['all']
            )
            db.session.add(superadmin_role)
            db.session.flush()

        # Create superadmin user
        superadmin = User(
            username='admin',
            email='admin@example.com',
            display_name='Administrator',
            is_active=True,
            is_superadmin=True
        )
        superadmin.set_password('admin')
        db.session.add(superadmin)
        
        # Add superadmin role to user
        superadmin.roles.append(superadmin_role)
        
        db.session.commit()
        
        click.echo('Superadmin created successfully:')
        click.echo('Username: admin')
        click.echo('Password: admin')
        
    except Exception as e:
        logger.error(f"Error creating superadmin: {str(e)}")
        db.session.rollback()
        click.echo(f'Error creating superadmin: {str(e)}')

# Export command
__all__ = ['create_superadmin_command'] 