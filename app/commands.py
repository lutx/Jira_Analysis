import click
from flask.cli import with_appcontext
from app.extensions import db
from app.models.role import Role
from app.models.user import User
from werkzeug.security import generate_password_hash

@click.command('init-db')
@with_appcontext
def init_db_command():
    """Inicjalizuje bazę danych podstawowymi danymi."""
    
    # Dodaj podstawowe role
    roles = {
        'user': 'Standardowy użytkownik',
        'admin': 'Administrator',
        'superadmin': 'Super Administrator'
    }
    
    for role_name, description in roles.items():
        if not Role.query.filter_by(name=role_name).first():
            role = Role(name=role_name, description=description)
            db.session.add(role)
    
    # Dodaj superadmina jeśli nie istnieje
    if not User.query.filter_by(username='admin').first():
        superadmin_role = Role.query.filter_by(name='superadmin').first()
        admin = User(
            username='admin',
            email='admin@example.com',
            display_name='Administrator',
            password_hash=generate_password_hash('admin'),  # Zmień to hasło w produkcji!
            is_active=True
        )
        admin.roles.append(superadmin_role)
        db.session.add(admin)
    
    db.session.commit()
    click.echo('Initialized the database with basic data.') 