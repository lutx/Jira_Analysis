import click
from flask.cli import with_appcontext
from app.extensions import db
from sqlalchemy import text

@click.command('update-db')
@with_appcontext
def update_db_command():
    """Update database schema."""
    try:
        # Add is_active column to portfolios if it doesn't exist
        db.session.execute(text("""
            ALTER TABLE portfolios ADD COLUMN is_active BOOLEAN DEFAULT 1;
        """))
        
        # Update existing portfolios to be active
        db.session.execute(text("""
            UPDATE portfolios SET is_active = 1 WHERE is_active IS NULL;
        """))
        
        # Create portfolio_projects table if it doesn't exist
        db.session.execute(text("""
            CREATE TABLE IF NOT EXISTS portfolio_projects (
                portfolio_id INTEGER NOT NULL,
                project_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (portfolio_id, project_id),
                FOREIGN KEY (portfolio_id) REFERENCES portfolios(id) ON DELETE CASCADE,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            );
        """))
        
        db.session.commit()
        click.echo('Database schema updated successfully.')
    except Exception as e:
        db.session.rollback()
        click.echo(f'Error updating database schema: {str(e)}', err=True)
        raise 