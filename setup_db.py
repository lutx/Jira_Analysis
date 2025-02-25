import os
import sys
from pathlib import Path
import sqlite3
import time

def setup_database():
    """Set up the database environment."""
    try:
        # Get absolute paths
        base_dir = Path(__file__).resolve().parent
        instance_dir = base_dir / 'instance'
        db_path = instance_dir / 'app.db'
        
        print(f"Setting up database environment...")
        print(f"Instance directory: {instance_dir}")
        print(f"Database path: {db_path}")
        
        # Create instance directory if it doesn't exist
        instance_dir.mkdir(parents=True, exist_ok=True)
        
        # Remove existing database file if it exists
        if db_path.exists():
            print("Removing existing database file...")
            try:
                db_path.unlink()
                time.sleep(1)
            except Exception as e:
                print(f"Warning: Could not remove existing database: {e}")
        
        # Create new database file
        print("Creating new database file...")
        try:
            # Create an empty SQLite database
            conn = sqlite3.connect(str(db_path))
            conn.close()
            
            # Set file permissions to be readable/writable
            os.chmod(db_path, 0o666)
            
            print(f"Database file created successfully at: {db_path}")
            return True
            
        except Exception as e:
            print(f"Error creating database file: {e}")
            return False
            
    except Exception as e:
        print(f"Error in setup: {e}")
        return False

if __name__ == "__main__":
    if setup_database():
        print("\nDatabase setup completed successfully!")
    else:
        print("\nDatabase setup failed!")
        sys.exit(1) 