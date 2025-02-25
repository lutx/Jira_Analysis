import click
import sys
from flask.cli import with_appcontext
from app.extensions import db
from app.models.user import User
from app.utils.auth_helpers import hash_password  # Upewnij się, że funkcja hash_password jest zaimplementowana

@click.command("create_superadmin")
@click.option("--username", prompt=True, help="Nazwa użytkownika dla superadmina.")
@click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True, help="Hasło dla superadmina.")
@click.option("--email", prompt=True, help="Email dla superadmina.")
@with_appcontext
def create_superadmin_command(username: str, password: str, email: str) -> None:
    """Utwórz nowego superadministratora."""
    existing_user = User.query.filter_by(username=username).first()
    if existing_user:
        click.echo(f"Użytkownik '{username}' już istnieje.")
        sys.exit(1)

    password_hash = hash_password(password)
    # Zakładamy, że pole is_superadmin oznacza, że użytkownik jest superadministratorem
    new_user = User(username=username, email=email, password_hash=password_hash, is_superadmin=True)
    db.session.add(new_user)
    db.session.commit()
    click.echo(f"Superadmin '{username}' został utworzony pomyślnie.") 