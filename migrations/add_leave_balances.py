"""Add leave balances table

This migration adds the leave balances table for tracking user leave allowances and usage.
"""

from app.extensions import db
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)

def upgrade():
    """Upgrade the database."""
    try:
        # Create leave_balances table
        db.session.execute(text("""
            CREATE TABLE IF NOT EXISTS leave_balances (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                year INTEGER NOT NULL,
                total_days INTEGER DEFAULT 26,
                used_days INTEGER DEFAULT 0,
                pending_days INTEGER DEFAULT 0,
                carried_over INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id),
                UNIQUE(user_id, year)
            );
        """))

        # Create indexes - execute one at a time
        db.session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_leave_balance_user ON leave_balances(user_id);
        """))

        db.session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_leave_balance_year ON leave_balances(year);
        """))

        # Initialize leave balances for existing users for current year
        db.session.execute(text("""
            INSERT INTO leave_balances (user_id, year)
            SELECT id, strftime('%Y', 'now')
            FROM users
            WHERE NOT EXISTS (
                SELECT 1 FROM leave_balances
                WHERE leave_balances.user_id = users.id
                AND leave_balances.year = strftime('%Y', 'now')
            );
        """))

        db.session.commit()
        logger.info("Successfully created leave_balances table and initialized balances")
        return True
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating leave_balances table: {str(e)}")
        return False

def downgrade():
    """Downgrade the database."""
    try:
        # Drop indexes first - execute one at a time
        db.session.execute(text("""
            DROP INDEX IF EXISTS idx_leave_balance_user;
        """))

        db.session.execute(text("""
            DROP INDEX IF EXISTS idx_leave_balance_year;
        """))

        # Drop the table
        db.session.execute(text("""
            DROP TABLE IF EXISTS leave_balances;
        """))

        db.session.commit()
        logger.info("Successfully removed leave_balances table")
        return True
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error removing leave_balances table: {str(e)}")
        return False 