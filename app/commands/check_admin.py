import click
from flask.cli import with_appcontext
from app.models.user import User
from app.models.role import Role
from app.extensions import db
import logging

logger = logging.getLogger(__name__)

@click.command('check-admin')
@with_appcontext
def check_admin_command():
    """Check superadmin details."""
    try:
        admin = User.query.filter_by(username='admin').first()
        if admin:
            click.echo(f'Admin exists:')
            click.echo(f'Username: {admin.username}')
            click.echo(f'Email: {admin.email}')
            click.echo(f'Is active: {admin.is_active}')
            click.echo(f'Is superadmin: {admin.is_superadmin}')
            click.echo(f'Roles: {[role.name for role in admin.roles]}')
        else:
            click.echo('Admin user not found')
    except Exception as e:
        logger.error(f"Error checking admin: {str(e)}")
        click.echo(f'Error checking admin: {str(e)}')

    # Sprawdź sesję i tokeny CSRF
    print("\n=== Session & CSRF ===")
    from flask import session, current_app
    print(f"Session type: {current_app.config['SESSION_TYPE']}")
    print(f"CSRF enabled: {current_app.config['WTF_CSRF_ENABLED']}")
    print(f"CSRF secret key set: {bool(current_app.config.get('WTF_CSRF_SECRET_KEY'))}") 