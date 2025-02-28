"""Add role enhancements

This migration adds job_function and hourly_rate columns to the roles table
and updates the permissions column to include new permissions.
"""

from app.extensions import db
from sqlalchemy import text
import logging
import json

logger = logging.getLogger(__name__)

def column_exists(column_name: str, table_name: str) -> bool:
    """Check if a column exists in a table."""
    result = db.session.execute(text(f"""
        SELECT COUNT(*) as count 
        FROM pragma_table_info('{table_name}') 
        WHERE name='{column_name}';
    """)).fetchone()
    return result[0] > 0

def upgrade():
    """Upgrade the database."""
    try:
        # Add new columns if they don't exist
        if not column_exists('job_function', 'roles'):
            db.session.execute(text("""
                ALTER TABLE roles 
                ADD COLUMN job_function VARCHAR(50);
            """))
            logger.info("Added job_function column to roles table")
        
        if not column_exists('hourly_rate', 'roles'):
            db.session.execute(text("""
                ALTER TABLE roles 
                ADD COLUMN hourly_rate FLOAT DEFAULT 0.0;
            """))
            logger.info("Added hourly_rate column to roles table")

        # Update existing roles with default job functions only if job_function is NULL
        db.session.execute(text("""
            UPDATE roles 
            SET job_function = 'developer' 
            WHERE job_function IS NULL 
            AND (name LIKE '%developer%' OR name LIKE '%dev%');
        """))
        
        db.session.execute(text("""
            UPDATE roles 
            SET job_function = 'qa' 
            WHERE job_function IS NULL 
            AND (name LIKE '%qa%' OR name LIKE '%test%');
        """))
        
        db.session.execute(text("""
            UPDATE roles 
            SET job_function = 'pm' 
            WHERE job_function IS NULL 
            AND (name LIKE '%manager%' OR name LIKE '%pm%');
        """))
        
        db.session.execute(text("""
            UPDATE roles 
            SET job_function = 'ba' 
            WHERE job_function IS NULL 
            AND (name LIKE '%analyst%' OR name LIKE '%ba%');
        """))

        # Add new permissions to existing admin roles using SQLite JSON functions
        db.session.execute(text("""
            UPDATE roles 
            SET permissions = json(
                CASE 
                    WHEN permissions IS NULL THEN '["manage_portfolios", "manage_assignments", "view_analytics", "manage_roles"]'
                    ELSE (
                        SELECT json_group_array(value)
                        FROM (
                            SELECT DISTINCT value
                            FROM json_each(permissions)
                            UNION ALL
                            SELECT value
                            FROM json_each('["manage_portfolios", "manage_assignments", "view_analytics", "manage_roles"]')
                        )
                    )
                END
            )
            WHERE name LIKE '%admin%';
        """))

        db.session.commit()
        logger.info("Successfully upgraded roles table with new columns and permissions")
        return True
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error upgrading roles table: {str(e)}")
        return False

def downgrade():
    """Downgrade the database."""
    try:
        # Only attempt to remove columns if they exist
        if column_exists('job_function', 'roles'):
            db.session.execute(text("""
                ALTER TABLE roles 
                DROP COLUMN job_function;
            """))
            logger.info("Removed job_function column from roles table")
        
        if column_exists('hourly_rate', 'roles'):
            db.session.execute(text("""
                ALTER TABLE roles 
                DROP COLUMN hourly_rate;
            """))
            logger.info("Removed hourly_rate column from roles table")

        # Remove new permissions from all roles using SQLite JSON functions
        db.session.execute(text("""
            UPDATE roles 
            SET permissions = json(
                CASE 
                    WHEN permissions IS NULL THEN '[]'
                    ELSE (
                        SELECT json_group_array(value)
                        FROM json_each(permissions)
                        WHERE value NOT IN (
                            'manage_portfolios',
                            'manage_assignments',
                            'view_analytics',
                            'manage_roles'
                        )
                    )
                END
            )
            WHERE permissions IS NOT NULL;
        """))

        db.session.commit()
        logger.info("Successfully downgraded roles table")
        return True
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error downgrading roles table: {str(e)}")
        return False 