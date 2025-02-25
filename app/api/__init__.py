from flask import Blueprint, request
from app.extensions import csrf

# Create API blueprint
api_bp = Blueprint('api', __name__, url_prefix='/api')

@csrf.exempt
def csrf_exempt(view):
    """Mark a view as CSRF exempt."""
    if isinstance(view, str):
        view_location = view
    else:
        view_location = '.'.join((view.__module__, view.__name__))
    
    return view

# Apply CSRF exemption to all API routes
csrf.exempt(api_bp)

# Import routes after blueprint creation to avoid circular imports
from app.api import admin, errors 

@api_bp.route('/health')
def health_check():
    return {'status': 'healthy'} 