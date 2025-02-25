from flask import Blueprint, Flask
import logging
from typing import Tuple, List

logger = logging.getLogger(__name__)

def create_blueprint(name: str, import_name: str) -> Blueprint:
    """Create a blueprint with consistent naming."""
    return Blueprint(name, import_name)

def register_blueprint_safely(app: Flask, blueprint: Blueprint, url_prefix: str = None) -> None:
    """Safely register a blueprint with error handling."""
    try:
        app.register_blueprint(blueprint, url_prefix=url_prefix)
        logger.info(f"Registered blueprint: {blueprint.name}")
    except Exception as e:
        logger.error(f"Error registering blueprint {blueprint.name}: {str(e)}")
        raise 