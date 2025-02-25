"""Views package initialization."""
from flask import Blueprint
import logging

views_bp = Blueprint('views', __name__)

# Import views after blueprint creation to avoid circular imports
from app.routes.views.views import *

logger = logging.getLogger(__name__)

__all__ = ['views_bp'] 