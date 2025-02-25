import os
from pathlib import Path
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

def test_flask_database():
    # Create basic Flask app
    app = Flask(__name__, instance_relative_config=True)
    
    # Get paths
    base_dir = Path(__file__).resolve().parent
    instance_dir = base_dir / 'instance'
    db_path = instance_dir / 'app.db'
    
    print(f"Base dir: {base_dir}")
    print(f"Instance dir: {instance_dir}")
    print(f"DB path: {db_path}")
    
    # Ensure instance directory exists
    instance_dir.mkdir(parents=True, exist_ok=True)
    
    # Configure Flask app
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'connect_args': {
            'timeout': 15,
            'check_same_thread': False
        }
    }
    
    # Initialize extensions
    db = SQLAlchemy(app)
    migrate = Migrate(app, db)
    
    # Create a test model
    class Test(db.Model):
        id = db.Column(db.Integer, primary_key=True)
    
    # Try database operations within app context
    with app.app_context():
        try:
            # Create tables
            db.create_all()
            print("Successfully created database tables")
            
            # Add test data
            test = Test()
            db.session.add(test)
            db.session.commit()
            print("Successfully added test data")
            
            # Query data
            result = Test.query.first()
            print(f"Successfully queried data: {result.id}")
            
        except Exception as e:
            print(f"Error with database: {e}")
            raise

if __name__ == "__main__":
    test_flask_database() 