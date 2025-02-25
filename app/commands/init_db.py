import click
from flask.cli import with_appcontext
from app.extensions import db
from app.models.role import Role
from app.models.user import User
import logging
from flask import current_app
from app.utils.roles import check_user_roles
from app.utils.db_check import verify_db_config
from app.utils.auth_helpers import hash_password

logger = logging.getLogger(__name__)

@click.command('init-db')
@with_appcontext
def init_db_command():
    """Inicjalizacja bazy danych."""
    # Usuń wszystkie istniejące tabele
    db.drop_all()
    
    # Utwórz wszystkie tabele na nowo
    db.create_all()
    
    # Utwórz domyślnego administratora
    admin = User(
        username='admin',
        email='admin@example.com',
        password_hash=hash_password('admin123'),
        is_superadmin=True
    )
    
    db.session.add(admin)
    try:
        db.session.commit()
        click.echo('Baza danych została zainicjalizowana.')
        click.echo('Utworzono konto administratora (login: admin, hasło: admin123)')
    except Exception as e:
        db.session.rollback()
        click.echo(f'Błąd podczas inicjalizacji bazy danych: {str(e)}')
        raise

@click.command('check-db')
@with_appcontext
def check_db_command():
    """Sprawdź stan bazy danych."""
    try:
        # Sprawdź czy tabela users istnieje
        users = User.query.all()
        click.echo(f'Znaleziono {len(users)} użytkowników w bazie:')
        for user in users:
            click.echo(f'- {user.username} ({"admin" if user.is_superadmin else "user"})')
    except Exception as e:
        click.echo(f'Błąd podczas sprawdzania bazy danych: {str(e)}')

@click.command('check-roles')
@with_appcontext
def check_roles_command():
    """Check and fix user roles."""
    check_user_roles()
    click.echo('Roles checked and fixed.')

# Export commands
__all__ = ['init_db_command', 'check_roles_command', 'check_db_command'] 