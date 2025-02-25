import os
import sqlite3
from pathlib import Path
import time
import shutil
from app import create_app
from app.models.database import db
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

def fix_database():
    """Fix database schema by adding missing columns."""
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
        return True
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Failed to update database schema: {e}")
        return False
    finally:
        if conn:
            conn.close()

def main():
    """Main function to fix database schema."""
    app = create_app()
    
    with app.app_context():
        logger.info("Starting database fix...")
        
        # Create backup
        if not backup_database():
            logger.error("Failed to create backup, aborting...")
            return
            
        # Fix database
        if fix_database():
            logger.info("Database fix completed successfully")
        else:
            logger.error("Failed to fix database")

if __name__ == '__main__':
    main() 