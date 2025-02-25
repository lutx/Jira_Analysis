import os
from pathlib import Path
import sqlite3

def test_database():
    # Get paths
    base_dir = Path(__file__).resolve().parent
    instance_dir = base_dir / 'instance'
    db_path = instance_dir / 'app.db'
    
    print(f"Base dir: {base_dir}")
    print(f"Instance dir: {instance_dir}")
    print(f"DB path: {db_path}")
    
    # Create instance directory
    instance_dir.mkdir(exist_ok=True)
    print(f"Instance directory exists: {instance_dir.exists()}")
    print(f"Instance directory writable: {os.access(instance_dir, os.W_OK)}")
    
    # Try to create and write to database
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute('CREATE TABLE IF NOT EXISTS test (id INTEGER PRIMARY KEY)')
        cursor.execute('INSERT INTO test (id) VALUES (1)')
        conn.commit()
        conn.close()
        print("Successfully created and wrote to database")
        print(f"Database exists: {db_path.exists()}")
        print(f"Database writable: {os.access(db_path, os.W_OK)}")
        print(f"Database size: {db_path.stat().st_size} bytes")
    except Exception as e:
        print(f"Error with database: {e}")

if __name__ == "__main__":
    test_database() 