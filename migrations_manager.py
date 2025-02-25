from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from app import create_app
from app.models.database import db

def run_migrations():
    """Run database migrations."""
    app = create_app()
    
    with app.app_context():
        # Initialize migrations
        migrate = Migrate(app, db)
        
        # Import all models to ensure they are tracked by migrations
        from app.models.project import Project
        from app.models.user import User
        from app.models.team import Team
        from app.models.role import Role
        from app.models.user_role import UserRole
        from app.models.team_membership import TeamMembership
        
        # Create the migrations directory if it doesn't exist
        from flask_migrate import init as init_migrations
        from flask_migrate import migrate as create_migration
        from flask_migrate import upgrade as apply_migration
        import os
        
        if not os.path.exists('migrations'):
            init_migrations()
        
        # Create a new migration
        create_migration()
        
        # Apply the migration
        apply_migration()

if __name__ == '__main__':
    run_migrations() 