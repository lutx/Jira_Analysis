from flask import Flask
import logging
from app.routes.main import main_bp
from app.routes.auth import auth_bp
from app.routes.views import views_bp
from app.routes.api import api_bp
from app.routes.admin import admin_bp
from app.routes.projects import projects_bp
from .portfolio import portfolio_bp
from .roles import roles_bp
from .reports import reports_bp
from .teams import teams_bp
from .users import users_bp
from .leaves import leaves_bp
from .assignments import assignments_bp
from .settings import settings_bp
from .health import health_bp
from .availability import availability_bp

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
            app.register_blueprint(portfolio_bp, url_prefix='/portfolio')
            logger.info("Registered portfolio_bp")
        except ImportError:
            logger.warning("Portfolio blueprint not found")
        
        app.register_blueprint(roles_bp)
        logger.info("Registered roles_bp")
        
        app.register_blueprint(reports_bp)
        logger.info("Registered reports_bp")
        
        app.register_blueprint(teams_bp)
        logger.info("Registered teams_bp")
        
        app.register_blueprint(users_bp)
        logger.info("Registered users_bp")
        
        app.register_blueprint(leaves_bp)
        logger.info("Registered leaves_bp")
        
        app.register_blueprint(assignments_bp)
        logger.info("Registered assignments_bp")
        
        app.register_blueprint(settings_bp)
        logger.info("Registered settings_bp")
        
        app.register_blueprint(health_bp)
        logger.info("Registered health_bp")
        
        app.register_blueprint(availability_bp)
        logger.info("Registered availability_bp")
        
        logger.info("Successfully registered all blueprints")
    except Exception as e:
        logger.error(f"Error registering blueprints: {str(e)}")
        raise

__all__ = ['register_blueprints'] 