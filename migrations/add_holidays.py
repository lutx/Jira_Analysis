"""Add holidays table

This migration adds the holidays table for tracking holidays and non-working days.
"""

from app.extensions import db
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)

def upgrade():
    """Upgrade the database."""
    try:
        # Create holidays table
        db.session.execute(text("""
            CREATE TABLE IF NOT EXISTS holidays (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE NOT NULL,
                name VARCHAR(100) NOT NULL,
                description TEXT,
                is_full_day BOOLEAN DEFAULT 1,
                country_code VARCHAR(2) DEFAULT 'PL',
                region VARCHAR(50),
                type VARCHAR(20) DEFAULT 'public',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by_id INTEGER,
                is_recurring BOOLEAN DEFAULT 0,
                FOREIGN KEY(created_by_id) REFERENCES users(id),
                UNIQUE(date, country_code)
            );
        """))

        # Create indexes
        db.session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_holiday_date ON holidays(date);
        """))

        # Add some default Polish holidays
        default_holidays = [
            ("2024-01-01", "New Year's Day", "public"),
            ("2024-01-06", "Epiphany", "public"),
            ("2024-04-01", "Easter Monday", "public"),
            ("2024-05-01", "Labour Day", "public"),
            ("2024-05-03", "Constitution Day", "public"),
            ("2024-05-19", "Pentecost Sunday", "public"),
            ("2024-05-30", "Corpus Christi", "public"),
            ("2024-08-15", "Assumption of the Blessed Virgin Mary", "public"),
            ("2024-11-01", "All Saints' Day", "public"),
            ("2024-11-11", "Independence Day", "public"),
            ("2024-12-25", "Christmas Day", "public"),
            ("2024-12-26", "Second Day of Christmas", "public")
        ]

        insert_stmt = text("""
            INSERT OR IGNORE INTO holidays (date, name, type, country_code, is_recurring)
            VALUES (:date, :name, :type, :country_code, :is_recurring)
        """)

        for date, name, holiday_type in default_holidays:
            db.session.execute(insert_stmt, {
                'date': date,
                'name': name,
                'type': holiday_type,
                'country_code': 'PL',
                'is_recurring': True
            })

        db.session.commit()
        logger.info("Successfully created holidays table and added default holidays")
        return True
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating holidays table: {str(e)}")
        return False

def downgrade():
    """Downgrade the database."""
    try:
        # Drop indexes first
        db.session.execute(text("""
            DROP INDEX IF EXISTS idx_holiday_date;
        """))

        # Drop the table
        db.session.execute(text("""
            DROP TABLE IF EXISTS holidays;
        """))

        db.session.commit()
        logger.info("Successfully removed holidays table")
        return True
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error removing holidays table: {str(e)}")
        return False 