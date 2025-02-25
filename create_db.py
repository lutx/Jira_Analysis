import os
from pathlib import Path
import sqlite3
from app import create_app, db
from app.config import Config

def setup_database():
    """Set up the database environment."""
    try:
        # Create app with config
        app = create_app(Config)
        
        # Get database path
        db_path = Path(app.config['DB_PATH'])
        print(f"Setting up database at: {db_path}")
        
        # Create parent directories if they don't exist
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Remove existing database if it exists
        if db_path.exists():
            db_path.unlink()
            print("Removed existing database")
        
        # Create new database file
        print("Creating new database file...")
        conn = sqlite3.connect(str(db_path))
        conn.close()
        
        # Set file permissions
        os.chmod(str(db_path), 0o666)
        print("Database file created successfully")
        
        # Initialize database with SQLAlchemy
        with app.app_context():
            print("Creating database tables...")
            db.create_all()
            print("Database tables created successfully")
            
            # Test database connection
            result = db.session.execute('SELECT 1').scalar()
            print(f"Database connection test successful: {result}")
            
            # Commit any pending transactions
            db.session.commit()
            
        return True
        
    except Exception as e:
        print(f"Error setting up database: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    setup_database() 