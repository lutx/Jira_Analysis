"""Add team tables and columns

This migration adds the team_projects table and portfolio_id column to teams table.
"""

from app.extensions import db
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)

def upgrade():
    """Upgrade the database."""
    try:
        # Create team_projects table if it doesn't exist
        db.session.execute(text("""
            CREATE TABLE IF NOT EXISTS team_projects (
                team_id INTEGER NOT NULL,
                project_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (team_id, project_id),
                FOREIGN KEY (team_id) REFERENCES teams (id),
                FOREIGN KEY (project_id) REFERENCES projects (id)
            );
        """))
        logger.info("Created team_projects table")

        # Add portfolio_id to teams table if it doesn't exist
        db.session.execute(text("""
            ALTER TABLE teams ADD COLUMN IF NOT EXISTS portfolio_id INTEGER REFERENCES portfolios(id);
        """))
        logger.info("Added portfolio_id column to teams table")

        # Create indexes
        db.session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_team_name ON teams(name);
            CREATE INDEX IF NOT EXISTS idx_team_leader ON teams(leader_id);
            CREATE INDEX IF NOT EXISTS idx_team_portfolio ON teams(portfolio_id);
            CREATE INDEX IF NOT EXISTS idx_team_active ON teams(is_active);
        """))
        logger.info("Created team indexes")

        db.session.commit()
        logger.info("Successfully upgraded team tables")
        return True
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error upgrading team tables: {str(e)}")
        return False

def downgrade():
    """Downgrade the database."""
    try:
        # Drop indexes first
        db.session.execute(text("""
            DROP INDEX IF EXISTS idx_team_name;
            DROP INDEX IF EXISTS idx_team_leader;
            DROP INDEX IF EXISTS idx_team_portfolio;
            DROP INDEX IF EXISTS idx_team_active;
        """))
        logger.info("Dropped team indexes")

        # Drop portfolio_id column from teams table
        db.session.execute(text("""
            ALTER TABLE teams DROP COLUMN IF EXISTS portfolio_id;
        """))
        logger.info("Dropped portfolio_id column from teams table")

        # Drop team_projects table
        db.session.execute(text("""
            DROP TABLE IF EXISTS team_projects;
        """))
        logger.info("Dropped team_projects table")

        db.session.commit()
        logger.info("Successfully downgraded team tables")
        return True
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error downgrading team tables: {str(e)}")
        return False 