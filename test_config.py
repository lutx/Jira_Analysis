from pathlib import Path
import logging

class Config:
    """Base configuration."""
    
    # Paths
    BASE_DIR = Path(__file__).parent.parent
    INSTANCE_PATH = BASE_DIR / "instance"
    DB_NAME = "app.db"
    DB_PATH = INSTANCE_PATH / DB_NAME
    
    # Database
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{DB_PATH}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "connect_args": {"check_same_thread": False}
    }
    
    # Flask
    SECRET_KEY = "dev-key-change-me"
    DEBUG = True
    
    @classmethod
    def init_paths(cls):
        """Initialize application paths."""
        try:
            cls.INSTANCE_PATH.mkdir(parents=True, exist_ok=True)
            test_file = cls.INSTANCE_PATH / "test.txt"
            test_file.write_text("test")
            test_file.unlink()
            logging.info(f"Paths initialized: {cls.INSTANCE_PATH}")
            return True
        except Exception as e:
            logging.error(f"Failed to initialize paths: {e}")
            raise
