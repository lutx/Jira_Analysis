from typing import Dict, Any
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from flask import current_app, request, abort
from flask_login import current_user
import logging

logger = logging.getLogger(__name__)

def has_role(user: Dict[str, Any], role: str) -> bool:
    """Check if user has specific role."""
    return role in user.get('roles', [])

def hash_password(password: str) -> str:
    """
    Hash a password using Werkzeug's security functions.
    
    Args:
        password: The plain text password to hash
        
    Returns:
        str: The hashed password
    """
    return generate_password_hash(password)

def verify_password(password_hash: str, password: str) -> bool:
    """
    Verify a password against its hash.
    
    Args:
        password_hash: The hashed password to check against
        password: The plain text password to verify
        
    Returns:
        bool: True if password matches, False otherwise
    """
    return check_password_hash(password_hash, password)

def require_auth(f):
    """Decorator to require authentication for a route."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(401)
        return f(*args, **kwargs)
    return decorated

def require_admin(f):
    """Decorator to require admin privileges for a route."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_superadmin:
            abort(403)
        return f(*args, **kwargs)
    return decorated 