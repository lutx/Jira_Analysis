import click
import logging
from flask.cli import with_appcontext
from app.extensions import db
from app.models import User, Role
from werkzeug.security import generate_password_hash
from flask import current_app
from app.commands.create_superadmin import create_superadmin_command
from app.commands.init_jira import init_jira_command
from app.commands.init_db import init_db_command
import os
import sqlite3
from datetime import datetime
import shutil

logger = logging.getLogger(__name__)

def register_commands(app):
    """Register Flask CLI commands."""
    app.cli.add_command(create_superadmin_command)
    app.cli.add_command(init_jira_command)
    app.cli.add_command(init_db_command)
    app.cli.add_command(fix_db_command)

def init_app(app):
    register_commands(app)

@click.command('test-jira')
def test_jira_command():
    """Test JIRA connection."""
    config = JiraConfig.get_active_config()
    if not config:
        click.echo("No active JIRA configuration found")
        return
    
    if config.test_connection():
        click.echo("JIRA connection successful!")
    else:
        click.echo("JIRA connection failed!")

@click.command('init-db')
@with_appcontext
def init_db_command():
    """Initialize the database."""
    try:
        # Create instance directory if it doesn't exist
        if not os.path.exists(current_app.instance_path):
            os.makedirs(current_app.instance_path)
            
        # Create database
        db.create_all()
        
        # Create default roles
        Role.get_or_create_default_role()
        Role.create_superadmin_role()
        
        click.echo('Initialized the database.')
    except Exception as e:
        click.echo(f'Error initializing database: {e}', err=True)

@click.command('create-superadmin')
@click.option('--username', default='admin', help='Superadmin username')
@click.option('--password', default='admin123', help='Superadmin password')
@click.option('--email', default='admin@example.com', help='Superadmin email')
@with_appcontext
def create_superadmin_command(username, password, email):
    """Create a superadmin user."""
    try:
        # Create instance directory if it doesn't exist
        if not os.path.exists(current_app.instance_path):
            os.makedirs(current_app.instance_path)

        # Check if superadmin role exists
        superadmin_role = Role.query.filter_by(name='superadmin').first()
        if not superadmin_role:
            superadmin_role = Role.create_superadmin_role()

        # Check if user already exists
        if User.query.filter_by(username=username).first():
            click.echo('Superadmin user already exists.')
            return

        # Create superadmin user
        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            is_active=True,
            is_superadmin=True
        )
        user.roles.append(superadmin_role)
        
        db.session.add(user)
        db.session.commit()
        click.echo('Superadmin user created successfully.')
        
    except Exception as e:
        db.session.rollback()
        click.echo(f'Error creating superadmin: {e}', err=True)

def backup_database():
    """Create a backup of the database."""
    try:
        db_path = 'instance/app.db'
        backup_path = f'instance/app.db.backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
        
        if os.path.exists(db_path):
            shutil.copy2(db_path, backup_path)
            logger.info(f"Database backup created at {backup_path}")
            return True
    except Exception as e:
        logger.error(f"Failed to create database backup: {e}")
        return False

def get_create_table_sql():
    """Get the SQL to create the projects table with all columns."""
    return """
    CREATE TABLE projects (
        id INTEGER NOT NULL PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        description TEXT,
        jira_key VARCHAR(10) UNIQUE,
        status VARCHAR(20),
        created_at DATETIME,
        updated_at DATETIME,
        portfolio_id INTEGER,
        jira_id VARCHAR(100) UNIQUE,
        last_sync DATETIME,
        is_active BOOLEAN DEFAULT 1,
        FOREIGN KEY(portfolio_id) REFERENCES portfolios (id)
    )
    """

@click.command('fix-db')
@with_appcontext
def fix_db_command():
    """Fix database schema by adding missing columns."""
    if not backup_database():
        logger.error("Failed to create backup, aborting...")
        return

    conn = None
    try:
        conn = sqlite3.connect('instance/app.db')
        cursor = conn.cursor()
        
        # Check if columns exist
        cursor.execute("PRAGMA table_info(projects)")
        columns = cursor.fetchall()
        column_names = {col[1] for col in columns}
        
        if 'jira_id' not in column_names or 'last_sync' not in column_names or 'is_active' not in column_names:
            # Rename current table to backup
            cursor.execute("ALTER TABLE projects RENAME TO projects_old")
            
            # Create new table with all columns
            cursor.execute(get_create_table_sql())
            
            # Copy data from old table
            cursor.execute("""
                INSERT INTO projects (
                    id, name, description, jira_key, status, 
                    created_at, updated_at, portfolio_id
                )
                SELECT 
                    id, name, description, jira_key, status,
                    created_at, updated_at, portfolio_id
                FROM projects_old
            """)
            
            # Drop old table
            cursor.execute("DROP TABLE projects_old")
            
            logger.info("Added jira_id, last_sync and is_active columns to projects table")
            
        conn.commit()
        logger.info("Database schema updated successfully")
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Failed to update database schema: {e}")
        raise
    finally:
        if conn:
            conn.close() 