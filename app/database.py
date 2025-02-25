import sqlite3
import json
from flask import current_app, g
import click
from flask.cli import with_appcontext
from app.utils.db import get_db, close_db, init_db
import os
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def get_db():
    """Get database connection."""
    if 'db' not in g:
        # Upewnij się, że katalog data istnieje
        os.makedirs(os.path.dirname(current_app.config['DATABASE']), exist_ok=True)
        g.db = sqlite3.connect(
            current_app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    """Initialize the database."""
    try:
        # Upewnij się, że katalog data istnieje
        os.makedirs(os.path.dirname(current_app.config['DATABASE']), exist_ok=True)
        
        db = get_db()
        cursor = db.cursor()
        
        # Wczytaj i wykonaj schemat bazy danych
        with current_app.open_resource('schema.sql') as f:
            cursor.executescript(f.read().decode('utf8'))
            
        db.commit()
        current_app.logger.info("Database initialized successfully")
        
    except Exception as e:
        current_app.logger.error(f"Database initialization error: {str(e)}")
        raise

def init_app(app):
    """Register database functions with the Flask app."""
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)

@click.command('init-db')
@with_appcontext
def init_db_command():
    """Clear existing data and create new tables."""
    init_db()
    current_app.logger.info('Database initialized successfully')