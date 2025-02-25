import sqlite3
import click
from flask import current_app, g
import logging
from werkzeug.security import generate_password_hash

logger = logging.getLogger(__name__)

def get_db():
    """Zwraca połączenie z bazą danych."""
    if 'db' not in g:
        g.db = sqlite3.connect(
            current_app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row

    return g.db

def close_db(e=None):
    """Zamyka połączenie z bazą danych."""
    db = g.pop('db', None)

    if db is not None:
        db.close()

def init_db():
    """Inicjalizuje bazę danych."""
    db = get_db()
    cursor = db.cursor()

    logger.info("Sprawdzam czy baza danych wymaga inicjalizacji...")
    
    # Sprawdź czy tabele już istnieją
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    existing_tables = {table['name'] for table in cursor.fetchall()}
    
    if existing_tables - {'sqlite_sequence'} == {'users', 'roles', 'user_roles', 'worklogs'}:
        logger.info("Baza danych już zainicjalizowana")
        return
        
    logger.info("Rozpoczynam inicjalizację bazy danych...")

    # Utwórz tabele
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_name TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            display_name TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1
        )
    """)
    logger.info("Utworzono tabelę users")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS roles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            description TEXT
        )
    """)
    logger.info("Utworzono tabelę roles")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_roles (
            user_name TEXT,
            role_id INTEGER,
            PRIMARY KEY (user_name, role_id),
            FOREIGN KEY (user_name) REFERENCES users (user_name),
            FOREIGN KEY (role_id) REFERENCES roles (id)
        )
    """)
    logger.info("Utworzono tabelę user_roles")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS worklogs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_name TEXT NOT NULL,
            jira_id TEXT NOT NULL,
            work_date TEXT NOT NULL,
            time_spent INTEGER NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_name) REFERENCES users (user_name)
        )
    """)
    logger.info("Utworzono tabelę worklogs")

    # Utwórz rolę superadmina jeśli nie istnieje
    logger.info("Tworzę rolę superadmina...")
    cursor.execute("""
        INSERT OR IGNORE INTO roles (name, description)
        VALUES ('superadmin', 'Pełne uprawnienia administracyjne')
    """)

    # Utwórz konto superadmina jeśli nie istnieje
    logger.info("Tworzę konto superadmina...")
    cursor.execute("""
        INSERT OR IGNORE INTO users (user_name, email, password_hash, display_name)
        VALUES (?, ?, ?, ?)
    """, (
        'admin',
        'admin@example.com',
        generate_password_hash('admin'),
        'Administrator'
    ))

    # Przypisz rolę superadmina
    cursor.execute("""
        INSERT OR IGNORE INTO user_roles (user_name, role_id)
        SELECT 'admin', id FROM roles WHERE name = 'superadmin'
    """)

    db.commit()
    logger.info("Baza danych i konto superadmina utworzone pomyślnie")

def create_superadmin():
    """Create superadmin user if not exists."""
    db = get_db()
    cursor = db.cursor()
    
    try:
        # Get superadmin credentials from environment
        email = current_app.config['SUPERADMIN_EMAIL']
        password = current_app.config['SUPERADMIN_PASSWORD']
        
        if not email or not password:
            logger.error("Superadmin credentials not found in environment variables")
            return False
            
        # Hash the password
        hashed_password = generate_password_hash(password)
        
        # Insert superadmin user
        cursor.execute('''
            INSERT OR IGNORE INTO users (user_name, email, password_hash, display_name, is_active)
            VALUES (?, ?, ?, ?, 1)
        ''', (email, email, hashed_password, 'Super Administrator'))
        
        # Get superadmin role id
        cursor.execute('SELECT id FROM roles WHERE name = ?', ('superadmin',))
        role_id = cursor.fetchone()['id']
        
        # Assign superadmin role
        cursor.execute('''
            INSERT OR IGNORE INTO user_roles (user_name, role_id, assigned_by)
            VALUES (?, ?, ?)
        ''', (email, role_id, 'system'))
        
        db.commit()
        logger.info(f"Superadmin account created successfully: {email}")
        return True
        
    except Exception as e:
        logger.error(f"Error creating superadmin account: {str(e)}")
        db.rollback()
        return False

def init_app(app):
    """Rejestruje funkcje bazy danych w aplikacji."""
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)

@click.command('init-db')
def init_db_command():
    """Komenda do inicjalizacji bazy danych."""
    init_db()
    click.echo('Baza danych została zainicjalizowana.') 