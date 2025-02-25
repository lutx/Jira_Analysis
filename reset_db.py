import os
import shutil
from pathlib import Path

def reset_database():
    """Reset the database and migrations."""
    # Get the base directory
    base_dir = Path(__file__).parent
    
    # Remove database file
    db_path = base_dir / 'instance' / 'app.db'
    if db_path.exists():
        os.remove(db_path)
        print(f"Removed database: {db_path}")
    
    # Remove migrations directory
    migrations_dir = base_dir / 'migrations'
    if migrations_dir.exists():
        shutil.rmtree(migrations_dir)
        print(f"Removed migrations directory: {migrations_dir}")
    
    # Remove __pycache__ directories
    for path in base_dir.rglob('__pycache__'):
        if path.is_dir():
            shutil.rmtree(path)
            print(f"Removed: {path}")
    
    print("Reset completed successfully!")

if __name__ == '__main__':
    reset_database() 