"""Add team capacity tables

This migration adds the team_capacities and team_allocations tables for tracking team capacity and workload.
"""

from app.extensions import db
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)

def upgrade():
    """Upgrade the database."""
    try:
        # Create team_capacities table
        db.session.execute(text("""
            CREATE TABLE IF NOT EXISTS team_capacities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_id INTEGER NOT NULL,
                year INTEGER NOT NULL,
                month INTEGER NOT NULL,
                working_days INTEGER NOT NULL,
                total_capacity FLOAT,
                allocated_capacity FLOAT DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(team_id) REFERENCES teams(id),
                UNIQUE(team_id, year, month)
            );
        """))

        # Create team_allocations table
        db.session.execute(text("""
            CREATE TABLE IF NOT EXISTS team_allocations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                capacity_id INTEGER NOT NULL,
                project_id INTEGER NOT NULL,
                allocated_hours FLOAT DEFAULT 0,
                priority INTEGER DEFAULT 1,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(capacity_id) REFERENCES team_capacities(id) ON DELETE CASCADE,
                FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE,
                UNIQUE(capacity_id, project_id)
            );
        """))

        # Create indexes
        db.session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_team_capacity_period ON team_capacities(team_id, year, month);
            CREATE INDEX IF NOT EXISTS idx_team_allocation_capacity ON team_allocations(capacity_id);
            CREATE INDEX IF NOT EXISTS idx_team_allocation_project ON team_allocations(project_id);
        """))

        # Initialize capacities for existing teams for current month
        db.session.execute(text("""
            INSERT INTO team_capacities (team_id, year, month, working_days)
            SELECT 
                id as team_id,
                strftime('%Y', 'now') as year,
                strftime('%m', 'now') as month,
                20 as working_days
            FROM teams
            WHERE NOT EXISTS (
                SELECT 1 FROM team_capacities
                WHERE team_capacities.team_id = teams.id
                AND team_capacities.year = strftime('%Y', 'now')
                AND team_capacities.month = strftime('%m', 'now')
            );
        """))

        db.session.commit()
        logger.info("Successfully created team capacity tables")
        return True
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating team capacity tables: {str(e)}")
        return False

def downgrade():
    """Downgrade the database."""
    try:
        # Drop indexes first
        db.session.execute(text("""
            DROP INDEX IF EXISTS idx_team_capacity_period;
            DROP INDEX IF EXISTS idx_team_allocation_capacity;
            DROP INDEX IF EXISTS idx_team_allocation_project;
        """))

        # Drop tables
        db.session.execute(text("""
            DROP TABLE IF EXISTS team_allocations;
            DROP TABLE IF EXISTS team_capacities;
        """))

        db.session.commit()
        logger.info("Successfully removed team capacity tables")
        return True
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error removing team capacity tables: {str(e)}")
        return False 