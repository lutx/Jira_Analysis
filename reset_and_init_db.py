import os
import shutil
from pathlib import Path
from flask import Flask, current_app
from flask_migrate import Migrate
from app import create_app, db

# Import all models to ensure they are registered with SQLAlchemy
from app.models import (
    db, Role, UserRole, User, Team, TeamMembership, Project, 
    Portfolio, portfolio_projects, ProjectAssignment, Worklog, 
    Setting, JiraConfig, UserAvailability, TokenBlocklist, Leave
)

import logging
from werkzeug.security import generate_password_hash
import subprocess
from sqlalchemy import inspect

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def clean_pycache():
    """Remove all __pycache__ directories."""
    root_dir = os.path.dirname(os.path.abspath(__file__))
    for dirpath, dirnames, filenames in os.walk(root_dir):
        if '__pycache__' in dirnames:
            cache_dir = os.path.join(dirpath, '__pycache__')
            shutil.rmtree(cache_dir)
            logger.info(f"Removed: {cache_dir}")

def reset_db():
    """Reset database and migrations."""
    print("Resetting database...")
    
    # Usuń bazę danych
    if os.path.exists('instance/app.db'):
        os.remove('instance/app.db')
        print("Database removed")
    
    # Usuń folder migracji
    migrations_dir = Path('migrations')
    if migrations_dir.exists():
        shutil.rmtree(migrations_dir)
        print("Migrations folder removed")
    
    # Usuń pliki cache Pythona
    for path in Path('.').rglob('__pycache__'):
        shutil.rmtree(path)
    print("Python cache files removed")

def create_tables():
    """Create all database tables."""
    logger.info("Creating database tables...")
    
    # Import all models to ensure they are registered
    from app.models import (
        db, Role, UserRole, User, Team, TeamMembership, Project, 
        Portfolio, portfolio_projects, ProjectAssignment, Worklog, 
        Setting, JiraConfig, UserAvailability, TokenBlocklist, Leave
    )
    
    # Drop all tables first
    logger.info("Dropping existing tables...")
    db.drop_all()
    db.session.commit()
    
    # Create tables
    logger.info("Creating tables...")
    db.create_all()
    db.session.commit()  # Commit the table creation
    
    # Verify tables were created
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    logger.info(f"Created tables: {', '.join(tables)}")
    
    # Define required tables and their dependencies
    required_tables = {
        'roles': ['id', 'name', 'permissions'],
        'users': ['id', 'username', 'email', 'password_hash'],
        'user_roles': ['user_id', 'role_id'],
        'settings': ['id', 'name', 'value'],
        'projects': ['id', 'name', 'jira_key'],
        'teams': ['id', 'name'],
        'project_assignments': ['id', 'project_id', 'user_id'],
        'worklogs': ['id', 'user_id', 'project_id', 'time_spent_seconds']
    }
    
    # Check if all required tables exist with their required columns
    missing_tables = []
    for table_name, required_columns in required_tables.items():
        if table_name not in tables:
            missing_tables.append(table_name)
            continue
        
        columns = [col['name'] for col in inspector.get_columns(table_name)]
        missing_columns = [col for col in required_columns if col not in columns]
        if missing_columns:
            logger.error(f"Table {table_name} is missing columns: {', '.join(missing_columns)}")
            missing_tables.append(f"{table_name} (missing columns)")
    
    if missing_tables:
        raise RuntimeError(f"Missing or incomplete tables: {', '.join(missing_tables)}")
    
    logger.info("All required tables and columns are present")

def create_roles(db_session) -> dict:
    """Create default roles."""
    roles = {}
    
    try:
        # Superadmin role
        superadmin_role = Role(
            name='superadmin',
            description='Superadmin role with all permissions',
            permissions=list(Role.PERMISSIONS.keys())
        )
        db_session.add(superadmin_role)
        logger.info(f"Created superadmin role with permissions: {superadmin_role.get_permissions()}")
        roles['superadmin'] = superadmin_role

        # Admin role
        admin_permissions = ['read', 'write', 'delete', 'admin', 'manage_teams', 
                           'manage_users', 'manage_projects', 'manage_worklogs', 
                           'manage_settings', 'view_reports']
        admin_role = Role(
            name='admin',
            description='Admin role with elevated permissions',
            permissions=admin_permissions
        )
        db_session.add(admin_role)
        logger.info(f"Created admin role with permissions: {admin_role.get_permissions()}")
        roles['admin'] = admin_role

        # User role
        user_permissions = ['read', 'write', 'view_reports']
        user_role = Role(
            name='user',
            description='Default user role',
            permissions=user_permissions
        )
        db_session.add(user_role)
        logger.info(f"Created user role with permissions: {user_role.get_permissions()}")
        roles['user'] = user_role

        # Commit all roles
        db_session.commit()
        
        # Verify roles were created correctly
        for role_name, role in roles.items():
            logger.info(f"Verifying role {role_name}:")
            logger.info(f"  - ID: {role.id}")
            logger.info(f"  - Name: {role.name}")
            logger.info(f"  - Permissions: {role.get_permissions()}")
        
        return roles
    except Exception as e:
        logger.error(f"Error creating roles: {str(e)}")
        db_session.rollback()
        raise

def create_superadmin(db_session, roles: dict):
    """Create superadmin user."""
    try:
        # Check if superadmin already exists
        superadmin = User.query.filter_by(username='admin').first()
        if superadmin:
            logger.info("Superadmin user already exists")
            return superadmin

        # Create new superadmin user without roles
        superadmin = User(
            username='admin',
            email='admin@example.com',
            display_name='Administrator',
            password_hash=generate_password_hash('admin'),
            is_active=True,
            is_superadmin=True,
            roles=[]  # Start with empty roles
        )

        # Add user to session first
        db_session.add(superadmin)
        db_session.flush()
        logger.info(f"Created superadmin user with ID: {superadmin.id}")

        # Add roles using SQLAlchemy relationship
        if 'superadmin' in roles and roles['superadmin']:
            superadmin.roles.append(roles['superadmin'])
            logger.info(f"Added superadmin role (id={roles['superadmin'].id}) to user")

        if 'admin' in roles and roles['admin']:
            superadmin.roles.append(roles['admin'])
            logger.info(f"Added admin role (id={roles['admin'].id}) to user")

        # Flush to ensure all relationships are created
        db_session.flush()

        # Verify the state
        logger.info(f"Superadmin user created with ID: {superadmin.id}")
        logger.info(f"Assigned roles: {[role.name for role in superadmin.roles]}")
        for role in superadmin.roles:
            logger.info(f"Role {role.name} (ID: {role.id}) permissions: {role.get_permissions()}")
        
        return superadmin
        
    except Exception as e:
        logger.error(f"Error creating superadmin: {str(e)}")
        db_session.rollback()
        raise

def create_default_settings(db_session):
    """Create default settings."""
    try:
        settings = [
            ('SYNC_INTERVAL', '3600'),
            ('LOG_LEVEL', '20'),
            ('CACHE_TIMEOUT', '300')
        ]
        
        for name, value in settings:
            setting = Setting(name=name, value=value)
            db_session.add(setting)
            logger.info(f"Created setting: {name}={value}")
        
        db_session.commit()
    except Exception as e:
        logger.error(f"Error creating settings: {str(e)}")
        db_session.rollback()
        raise

def create_jira_config(app):
    """Create JIRA configuration."""
    with app.app_context():
        if all([
            app.config.get('JIRA_URL'),
            app.config.get('JIRA_USERNAME'),
            app.config.get('JIRA_API_TOKEN')
        ]):
            jira_config = JiraConfig.query.filter_by(is_active=True).first()
            if not jira_config:
                jira_config = JiraConfig(
                    url=app.config['JIRA_URL'],
                    username=app.config['JIRA_USERNAME'],
                    api_token=app.config['JIRA_API_TOKEN'],
                    is_active=True
                )
                db.session.add(jira_config)
                db.session.commit()
                logger.info("Created JIRA configuration")

def setup_database():
    """Set up database with initial data."""
    logger.info("Starting database setup...")
    
    app = create_app()
    
    with app.app_context():
        try:
            # Create all tables
            create_tables()
            
            # Step 1: Create roles in a separate session
            session = db.session()
            try:
                roles = create_roles(session)
                session.commit()
                logger.info("Roles created successfully")
            except Exception as e:
                session.rollback()
                logger.error(f"Error creating roles: {str(e)}")
                raise
            finally:
                session.close()

            # Step 2: Create settings in a separate session
            session = db.session()
            try:
                create_default_settings(session)
                session.commit()
                logger.info("Settings created successfully")
            except Exception as e:
                session.rollback()
                logger.error(f"Error creating settings: {str(e)}")
                raise
            finally:
                session.close()

            # Step 3: Create superadmin in a separate session
            session = db.session()
            try:
                # Fetch existing roles
                roles = {
                    'superadmin': Role.query.filter_by(name='superadmin').first(),
                    'admin': Role.query.filter_by(name='admin').first(),
                    'user': Role.query.filter_by(name='user').first()
                }
                
                if not all(roles.values()):
                    raise ValueError("Not all required roles exist in database")
                
                create_superadmin(session, roles)
                session.commit()
                logger.info("Superadmin created successfully")
            except Exception as e:
                session.rollback()
                logger.error(f"Error creating superadmin: {str(e)}")
                raise
            finally:
                session.close()

            # Verify final state
            session = db.session()
            try:
                # Check roles
                all_roles = Role.query.all()
                logger.info(f"Total roles in database: {len(all_roles)}")
                for role in all_roles:
                    logger.info(f"Role: {role.name}, Permissions: {role.get_permissions()}")

                # Check admin user
                admin = User.query.filter_by(username='admin').first()
                if admin:
                    logger.info(f"Admin user exists with roles: {[r.name for r in admin.roles]}")
                    logger.info(f"Admin permissions: {[p for r in admin.roles for p in r.get_permissions()]}")
                else:
                    logger.error("Admin user not found!")
                
            finally:
                session.close()

            logger.info("Database setup completed successfully")
                
        except Exception as e:
            logger.error(f"Error during database setup: {str(e)}")
            raise

if __name__ == '__main__':
    # Clean pycache
    clean_pycache()
    
    # Reset database
    reset_db()
    
    # Set up database
    setup_database() 