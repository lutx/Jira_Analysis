"""Add reports tables

This migration adds the reports and report_results tables for storing report configurations and results.
"""

from app.extensions import db
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)

def upgrade():
    """Upgrade the database."""
    try:
        # Create reports table
        db.session.execute(text("""
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(100) NOT NULL,
                description TEXT,
                report_type VARCHAR(50) NOT NULL,
                parameters TEXT,
                schedule VARCHAR(100),
                created_by_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_run_at TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                FOREIGN KEY(created_by_id) REFERENCES users(id)
            );
        """))

        # Create report_results table
        db.session.execute(text("""
            CREATE TABLE IF NOT EXISTS report_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_id INTEGER NOT NULL,
                execution_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status VARCHAR(20) DEFAULT 'pending',
                result_data TEXT,
                error_message TEXT,
                execution_time FLOAT,
                FOREIGN KEY(report_id) REFERENCES reports(id) ON DELETE CASCADE
            );
        """))

        # Create indexes
        db.session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_report_type ON reports(report_type);
            CREATE INDEX IF NOT EXISTS idx_report_created_by ON reports(created_by_id);
            CREATE INDEX IF NOT EXISTS idx_report_result_date ON report_results(execution_date);
            CREATE INDEX IF NOT EXISTS idx_report_result_status ON report_results(status);
        """))

        # Add some default reports
        default_reports = [
            (
                "Monthly Leave Usage",
                "Monthly report of leave usage by team member",
                "leave_usage",
                '{"team_id": null}'
            ),
            (
                "Team Availability Overview",
                "Overview of team member availability",
                "team_availability",
                '{"team_id": null}'
            ),
            (
                "Project Cost Analysis",
                "Analysis of project costs based on role rates",
                "cost_tracking",
                '{"project_id": null}'
            ),
            (
                "Portfolio Resource Allocation",
                "Analysis of resource allocation across portfolio projects",
                "project_allocation",
                '{"portfolio_id": null}'
            )
        ]

        for name, description, report_type, parameters in default_reports:
            db.session.execute(text(f"""
                INSERT OR IGNORE INTO reports (name, description, report_type, parameters)
                VALUES (
                    '{name}',
                    '{description}',
                    '{report_type}',
                    '{parameters}'
                );
            """))

        db.session.commit()
        logger.info("Successfully created reports tables and added default reports")
        return True
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating reports tables: {str(e)}")
        return False

def downgrade():
    """Downgrade the database."""
    try:
        # Drop indexes first
        db.session.execute(text("""
            DROP INDEX IF EXISTS idx_report_type;
            DROP INDEX IF EXISTS idx_report_created_by;
            DROP INDEX IF EXISTS idx_report_result_date;
            DROP INDEX IF EXISTS idx_report_result_status;
        """))

        # Drop tables
        db.session.execute(text("""
            DROP TABLE IF EXISTS report_results;
            DROP TABLE IF EXISTS reports;
        """))

        db.session.commit()
        logger.info("Successfully removed reports tables")
        return True
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error removing reports tables: {str(e)}")
        return False 