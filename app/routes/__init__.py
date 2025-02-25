from flask import Flask
import logging
from app.routes.main import main_bp
from app.routes.auth import auth_bp
from app.routes.views import views_bp
from app.routes.api import api_bp
from app.routes.admin import admin_bp
from app.routes.projects import projects_bp

logger = logging.getLogger(__name__)

def register_blueprints(app: Flask) -> None:
    """Register Flask blueprints."""
    try:
        logger.info("Starting blueprint registration")
        
        # Register core blueprints in correct order
        app.register_blueprint(main_bp)
        logger.info("Registered main_bp")
        
        app.register_blueprint(auth_bp, url_prefix='/auth')
        logger.info("Registered auth_bp")
        
        app.register_blueprint(views_bp)
        logger.info("Registered views_bp")
        
        app.register_blueprint(api_bp, url_prefix='/api/v1')
        logger.info("Registered api_bp")
        
        app.register_blueprint(admin_bp, url_prefix='/admin')
        logger.info("Registered admin_bp")
        
        app.register_blueprint(projects_bp)
        logger.info("Registered projects_bp")
        
        # Import and register optional blueprints
        try:
            from app.routes.portfolio import portfolio_bp
            app.register_blueprint(portfolio_bp, url_prefix='/portfolio')
            logger.info("Registered portfolio_bp")
        except ImportError:
            logger.warning("Portfolio blueprint not found")
        
        logger.info("Successfully registered all blueprints")
    except Exception as e:
        logger.error(f"Error registering blueprints: {str(e)}")
        raise

__all__ = ['register_blueprints'] 