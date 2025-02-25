from app.database import get_db
from datetime import datetime, timedelta
import random
from flask import current_app
import logging
from werkzeug.security import generate_password_hash as hash_password

logger = logging.getLogger(__name__)

def reset_database():
    """Wyczyść i zresetuj bazę danych."""
    try:
        db = get_db()
        
        # Utwórz tabele na nowo
        with current_app.open_resource('schema.sql') as f:
            db.executescript(f.read().decode('utf8'))
        
        db.commit()
        return True
    except Exception as e:
        logger.error(f"Error resetting database: {str(e)}")
        return False

def seed_database():
    """Seed the database with sample data."""
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Reset database
        with current_app.open_resource('schema.sql') as f:
            db.executescript(f.read().decode('utf8'))
        
        # Create users with hashed passwords
        users = [
            ('admin', 'admin@example.com', hash_password('admin')),
            ('dev1', 'dev1@example.com', hash_password('dev1')),
            ('dev2', 'dev2@example.com', hash_password('dev2')),
            ('tester1', 'tester1@example.com', hash_password('tester1'))
        ]
        
        user_ids = {}
        for username, email, password_hash in users:
            cursor.execute(
                'INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)',
                (username, email, password_hash)
            )
            user_ids[username] = cursor.lastrowid
        
        # Get role IDs
        cursor.execute('SELECT id, name FROM roles')
        role_ids = {row['name']: row['id'] for row in cursor.fetchall()}
        
        # Assign roles to users
        user_roles = [
            (user_ids['admin'], role_ids['admin']),
            (user_ids['dev1'], role_ids['user']),
            (user_ids['dev2'], role_ids['user']),
            (user_ids['tester1'], role_ids['user'])
        ]
        
        for user_id, role_id in user_roles:
            cursor.execute(
                'INSERT INTO user_roles (user_id, role_id) VALUES (?, ?)',
                (user_id, role_id)
            )
        
        # Create portfolios
        portfolios = [
            ('Portfolio 1', 'First portfolio', 'Client A'),
            ('Portfolio 2', 'Second portfolio', 'Client B')
        ]
        
        portfolio_ids = {}
        for name, desc, client in portfolios:
            cursor.execute(
                '''INSERT INTO portfolios 
                   (name, description, client_name, created_by) 
                   VALUES (?, ?, ?, ?)''',
                (name, desc, client, 'admin')
            )
            portfolio_ids[name] = cursor.lastrowid
        
        # Create projects
        projects = [
            (portfolio_ids['Portfolio 1'], 'PROJ1', 'Project 1', 'active'),
            (portfolio_ids['Portfolio 1'], 'PROJ2', 'Project 2', 'active'),
            (portfolio_ids['Portfolio 2'], 'PROJ3', 'Project 3', 'active')
        ]
        
        for portfolio_id, key, name, status in projects:
            cursor.execute(
                '''INSERT INTO portfolio_projects 
                   (portfolio_id, project_key, name, status, assigned_by) 
                   VALUES (?, ?, ?, ?, ?)''',
                (portfolio_id, key, name, status, 'admin')
            )
        
        # Add leave requests
        leaves = [
            (user_ids['dev1'], datetime.now(), datetime.now() + timedelta(days=5), 'vacation', 'pending'),
            (user_ids['dev2'], datetime.now() + timedelta(days=10), datetime.now() + timedelta(days=15), 'vacation', 'approved'),
            (user_ids['tester1'], datetime.now() + timedelta(days=20), datetime.now() + timedelta(days=22), 'sick', 'approved')
        ]
        
        for user_id, start_date, end_date, leave_type, status in leaves:
            cursor.execute(
                '''INSERT INTO leave_requests 
                   (user_id, start_date, end_date, leave_type, status) 
                   VALUES (?, ?, ?, ?, ?)''',
                (user_id, start_date, end_date, leave_type, status)
            )
        
        # Add worklogs
        for _ in range(50):
            user_id = random.choice(list(user_ids.values()))
            project = random.choice(['PROJ1', 'PROJ2', 'PROJ3'])
            started = datetime.now() - timedelta(days=random.randint(0, 30))
            hours = random.randint(1, 8)
            
            cursor.execute(
                '''INSERT INTO worklogs 
                   (user_id, project_key, issue_key, comment, time_spent, started) 
                   VALUES (?, ?, ?, ?, ?, ?)''',
                (user_id, project, f'TASK-{random.randint(1, 100)}',
                 f'Work on task {random.randint(1, 100)}',
                 hours * 3600, started)
            )
        
        db.commit()
        logger.info("Database seeded successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error seeding database: {str(e)}")
        if db:
            db.rollback()
        return False

def create_superadmin():
    """Create superadmin account if it doesn't exist."""
    db = get_db()
    try:
        # Get superadmin credentials from config
        email = current_app.config['SUPERADMIN_EMAIL']
        password = current_app.config['SUPERADMIN_PASSWORD']
        
        if not email or not password:
            logger.warning("Superadmin credentials not configured")
            return False
            
        # Check if superadmin already exists
        cursor = db.execute('SELECT 1 FROM users WHERE email = ?', (email,))
        if cursor.fetchone():
            logger.info("Superadmin account already exists")
            return True
            
        # Create superadmin user
        db.execute('''
            INSERT INTO users (email, password, display_name, is_active, role)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            email,
            hash_password(password),
            'Super Administrator',
            True,
            'superadmin'
        ))
        
        db.commit()
        logger.info("Superadmin account created successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error creating superadmin account: {str(e)}")
        db.rollback()
        return False

def reset_user_password(username: str, new_password: str) -> bool:
    """Reset user password."""
    try:
        db = get_db()
        cursor = db.cursor()
        
        password_hash = hash_password(new_password)
        cursor.execute("""
            UPDATE users 
            SET password_hash = ? 
            WHERE username = ?
        """, (password_hash, username))
        
        if cursor.rowcount == 0:
            logger.warning(f"User not found: {username}")
            return False
            
        db.commit()
        logger.info(f"Password reset for user: {username}")
        return True
        
    except Exception as e:
        logger.error(f"Error resetting password for {username}: {str(e)}")
        db.rollback()
        return False

if __name__ == '__main__':
    seed_database() 