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

def column_exists(cursor, table_name, column_name):
    """Check if a column exists in a table."""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    return any(col[1] == column_name for col in columns)

def create_team_indexes():
    """Create indexes for the teams table."""
    conn = None
    try:
        conn = sqlite3.connect('instance/app.db')
        cursor = conn.cursor()
        
        # Create indexes if they don't exist
        indexes = [
            ('idx_team_name', 'teams', 'name'),
            ('idx_team_leader', 'teams', 'leader_id'),
            ('idx_team_portfolio', 'teams', 'portfolio_id'),
            ('idx_team_active', 'teams', 'is_active')
        ]
        
        for index_name, table_name, column_name in indexes:
            try:
                cursor.execute(f"""
                    CREATE INDEX IF NOT EXISTS {index_name} 
                    ON {table_name} ({column_name})
                """)
                logger.info(f"Created index {index_name}")
            except Exception as e:
                logger.warning(f"Error creating index {index_name}: {e}")
        
        conn.commit()
        logger.info("Team indexes created successfully")
        return True
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Failed to create team indexes: {e}")
        return False
    finally:
        if conn:
            conn.close()

def fix_team_tables():
    """Fix team tables structure."""
    conn = None
    try:
        conn = sqlite3.connect('instance/app.db')
        cursor = conn.cursor()
        
        # Create team_projects table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS team_projects (
                team_id INTEGER NOT NULL,
                project_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (team_id, project_id),
                FOREIGN KEY (team_id) REFERENCES teams (id),
                FOREIGN KEY (project_id) REFERENCES projects (id)
            );
        """)
        logger.info("Created team_projects table")
        
        # Add portfolio_id to teams table if it doesn't exist
        if not column_exists(cursor, 'teams', 'portfolio_id'):
            cursor.execute("""
                ALTER TABLE teams ADD COLUMN portfolio_id INTEGER 
                REFERENCES portfolios(id);
            """)
            logger.info("Added portfolio_id column to teams table")
        
        conn.commit()
        logger.info("Team tables fixed successfully")
        return True
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Failed to fix team tables: {e}")
        return False
    finally:
        if conn:
            conn.close()

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
            cursor.execute("""
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
            """)
            
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

def create_teams_table():
    """Create teams table if it doesn't exist."""
    conn = None
    try:
        conn = sqlite3.connect('instance/app.db')
        cursor = conn.cursor()
        
        # Create teams table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS teams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(100) NOT NULL,
                description TEXT,
                leader_id INTEGER,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                portfolio_id INTEGER,
                FOREIGN KEY (leader_id) REFERENCES users (id),
                FOREIGN KEY (portfolio_id) REFERENCES portfolios (id)
            );
        """)
        logger.info("Created teams table")
        
        conn.commit()
        logger.info("Teams table created successfully")
        return True
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Failed to create teams table: {e}")
        return False
    finally:
        if conn:
            conn.close()

def create_team_memberships_table():
    """Create team_memberships table if it doesn't exist."""
    conn = None
    try:
        # Ensure the instance directory exists
        if not os.path.exists('instance'):
            os.makedirs('instance')
            logger.info("Created instance directory")
        
        # Check if database file exists
        db_path = 'instance/app.db'
        if not os.path.exists(db_path):
            logger.info(f"Database file does not exist at {db_path}, it will be created")
        
        # Connect to database with foreign key support
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        cursor = conn.cursor()
        
        # Check if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='team_memberships'")
        if cursor.fetchone():
            logger.info("Team memberships table already exists, dropping it...")
            cursor.execute("DROP TABLE IF EXISTS team_memberships")
            conn.commit()
        
        # Create team_memberships table
        create_table_sql = """
            CREATE TABLE team_memberships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                role VARCHAR(50) DEFAULT 'member',
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (team_id) REFERENCES teams (id),
                FOREIGN KEY (user_id) REFERENCES users (id),
                UNIQUE (team_id, user_id)
            )
        """
        try:
            cursor.execute(create_table_sql)
            conn.commit()
            logger.info("Created team_memberships table successfully")
        except Exception as e:
            logger.error(f"Failed to create team_memberships table: {str(e)}")
            logger.error(f"SQL that failed: {create_table_sql}")
            raise
        
        # Create indexes one by one with error handling
        indexes = [
            ("idx_team_membership_team", "team_id"),
            ("idx_team_membership_user", "user_id"),
            ("idx_team_membership_active", "is_active")
        ]
        
        for index_name, column in indexes:
            try:
                cursor.execute(f"""
                    CREATE INDEX IF NOT EXISTS {index_name} 
                    ON team_memberships ({column})
                """)
                conn.commit()
                logger.info(f"Created index {index_name} on {column}")
            except Exception as e:
                logger.warning(f"Failed to create index {index_name}: {str(e)}")
        
        return True
    except Exception as e:
        if conn:
            try:
                conn.rollback()
            except:
                pass
        logger.error(f"Failed to create team_memberships table: {str(e)}")
        return False
    finally:
        if conn:
            try:
                conn.close()
            except Exception as e:
                logger.error(f"Error closing database connection: {str(e)}")

def main():
    """Main function to fix database schema."""
    try:
        app = create_app()
        
        with app.app_context():
            logger.info("Starting database fix...")
            
            # Create backup
            if not backup_database():
                logger.error("Failed to create backup, aborting...")
                return
            
            # Create teams table
            if create_teams_table():
                logger.info("Teams table created successfully")
            else:
                logger.error("Failed to create teams table")
                return
            
            # Create team memberships table
            if create_team_memberships_table():
                logger.info("Team memberships table created successfully")
            else:
                logger.error("Failed to create team memberships table")
                return
            
            # Fix database
            if fix_database():
                logger.info("Database fix completed successfully")
            else:
                logger.error("Failed to fix database")
                return
            
            # Fix team tables
            if fix_team_tables():
                logger.info("Team tables fixed successfully")
            else:
                logger.error("Failed to fix team tables")
                return
            
            # Create team indexes
            if create_team_indexes():
                logger.info("Team indexes created successfully")
            else:
                logger.error("Failed to create team indexes")
                
            logger.info("Database fix completed successfully")
    except Exception as e:
        logger.error(f"Unexpected error during database fix: {str(e)}")
        raise

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        raise 