"""Add is_active column to projects table

Revision ID: add_is_active
Revises: 
Create Date: 2024-02-25 09:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_is_active'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Create a new table with all columns
    op.execute("""
    CREATE TABLE projects_new (
        id INTEGER NOT NULL PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        description TEXT,
        jira_key VARCHAR(10) UNIQUE,
        jira_id VARCHAR(100) UNIQUE,
        status VARCHAR(20) DEFAULT 'active',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        last_sync DATETIME,
        is_active BOOLEAN DEFAULT 1,
        portfolio_id INTEGER REFERENCES portfolios(id)
    )
    """)
    
    # Copy data from old table
    op.execute("""
    INSERT INTO projects_new (
        id, name, description, jira_key, jira_id, status,
        created_at, updated_at, last_sync, portfolio_id
    )
    SELECT 
        id, name, description, jira_key, jira_id, status,
        created_at, updated_at, last_sync, portfolio_id
    FROM projects
    """)
    
    # Drop old table
    op.execute("DROP TABLE projects")
    
    # Rename new table
    op.execute("ALTER TABLE projects_new RENAME TO projects")

def downgrade():
    # Remove is_active column
    op.execute("""
    CREATE TABLE projects_old (
        id INTEGER NOT NULL PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        description TEXT,
        jira_key VARCHAR(10) UNIQUE,
        jira_id VARCHAR(100) UNIQUE,
        status VARCHAR(20) DEFAULT 'active',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        last_sync DATETIME,
        portfolio_id INTEGER REFERENCES portfolios(id)
    )
    """)
    
    # Copy data back
    op.execute("""
    INSERT INTO projects_old (
        id, name, description, jira_key, jira_id, status,
        created_at, updated_at, last_sync, portfolio_id
    )
    SELECT 
        id, name, description, jira_key, jira_id, status,
        created_at, updated_at, last_sync, portfolio_id
    FROM projects
    """)
    
    # Drop new table
    op.execute("DROP TABLE projects")
    
    # Rename old table back
    op.execute("ALTER TABLE projects_old RENAME TO projects") 