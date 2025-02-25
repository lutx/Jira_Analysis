import click
import logging
import os
from app.database.models import db, User, Role, UserRole

logger = logging.getLogger(__name__)

def setup_app(app):
    """Initial application setup."""
    try:
        click.echo("🚀 Starting application setup...")
        
        with app.app_context():
            # 1. Upewnij się że katalog instance istnieje
            instance_path = os.path.join(app.root_path, '..', 'instance')
            os.makedirs(instance_path, exist_ok=True)
            click.echo("✓ Instance directory created")
            
            # 2. Usuń starą bazę jeśli istnieje
            db_path = os.path.join(instance_path, 'worklogs.db')
            if os.path.exists(db_path):
                os.remove(db_path)
                click.echo("✓ Old database removed")
            
            # 3. Inicjalizacja bazy danych
            db.create_all()
            click.echo("✓ Database tables created")
            
            # 4. Tworzenie konta administratora
            superadmin = User(
                user_name=app.config['SUPERADMIN_EMAIL'],
                email=app.config['SUPERADMIN_EMAIL'],
                display_name='Super Administrator',
                is_active=True
            )
            
            password = app.config['SUPERADMIN_PASSWORD']
            superadmin.set_password(password)
            
            db.session.add(superadmin)
            
            # Tworzenie roli superadmina
            superadmin_role = Role(
                name='superadmin',
                description='Super Administrator',
                permissions='["all"]',
                is_system=True
            )
            db.session.add(superadmin_role)
            db.session.flush()  # Aby uzyskać ID roli
            
            # Przypisanie roli do użytkownika
            user_role = UserRole(
                user_name=superadmin.user_name,
                role_id=superadmin_role.id,
                assigned_by='system'
            )
            db.session.add(user_role)
            
            db.session.commit()
            click.echo("✓ Admin account created")
            
            # 5. Weryfikacja
            user = User.query.filter_by(email=superadmin.email).first()
            if user and user.check_password(password):
                click.echo("\n✨ Setup completed successfully!")
                click.echo("\nYou can now log in with:")
                click.echo(f"Email: {superadmin.email}")
                click.echo(f"Password: {password}")
            else:
                click.echo("\n⚠️ Warning: Admin account verification failed!")
        
    except Exception as e:
        logger.error(f"Setup error: {str(e)}")
        click.echo(f"\n❌ Error during setup: {str(e)}")
        if 'db' in locals():
            db.session.rollback()
        raise 