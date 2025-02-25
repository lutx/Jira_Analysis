from app import create_app
from app.models.database import db
from sqlalchemy import text

def update_database():
    """Update database schema to add new columns."""
    app = create_app()
    
    with app.app_context():
        # Check if columns exist
        with db.engine.connect() as conn:
            # Check if jira_id column exists
            result = conn.execute(text("""
                SELECT COUNT(*) 
                FROM pragma_table_info('projects') 
                WHERE name='jira_id'
            """))
            has_jira_id = result.scalar() > 0

            # Check if last_sync column exists
            result = conn.execute(text("""
                SELECT COUNT(*) 
                FROM pragma_table_info('projects') 
                WHERE name='last_sync'
            """))
            has_last_sync = result.scalar() > 0

            # Add columns if they don't exist
            if not has_jira_id:
                conn.execute(text(
                    "ALTER TABLE projects ADD COLUMN jira_id VARCHAR(100) UNIQUE"
                ))
                print("Added jira_id column")

            if not has_last_sync:
                conn.execute(text(
                    "ALTER TABLE projects ADD COLUMN last_sync DATETIME"
                ))
                print("Added last_sync column")

            db.session.commit()
            print("Database schema updated successfully")

if __name__ == '__main__':
    update_database() 