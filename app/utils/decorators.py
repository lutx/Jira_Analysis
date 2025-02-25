from functools import wraps
from flask import g, redirect, url_for, abort, flash, request, current_app, jsonify
from typing import List, Union, Callable
import logging
from app.utils.auth_helpers import has_role
from flask_login import current_user

logger = logging.getLogger(__name__)

def auth_required(roles: Union[List[str], None] = None) -> Callable:
    """Ujednolicony dekorator do autoryzacji"""
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                if request.is_json:
                    return jsonify({'error': 'Authentication required'}), 401
                flash('Proszę się zalogować, aby uzyskać dostęp.', 'warning')
                return redirect(url_for('auth.login', next=request.url))
            
            if roles and not any(current_user.has_role(role) for role in roles):
                if request.is_json:
                    return jsonify({'error': 'Permission denied'}), 403
                flash('Brak uprawnień do dostępu do tej strony.', 'error')
                return redirect(url_for('main.dashboard'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def admin_required(f):
    return auth_required(['admin'])(f)

def superadmin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
            
        # Dodaj logowanie dla debugowania
        logger.info(f"User: {current_user.email}")
        logger.info(f"Is superadmin: {current_user.is_superadmin}")
        logger.info(f"Roles: {current_user.roles}")
        
        if not current_user.is_superadmin:
            logger.warning(
                f'Permission denied for user {current_user.username} '
                f'accessing {request.path}. Not a superadmin.'
            )
            flash('Wymagane uprawnienia superadmina.', 'danger')
            return redirect(url_for('views.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(role_name):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            if not current_user.is_superadmin and not current_user.has_role(role_name):
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def check_project_access(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        project_id = kwargs.get('project_id')
        if not project_id or not current_user.can_access_project(project_id):
            flash('You do not have access to this project.', 'error')
            return redirect(url_for('views.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def check_team_access(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        team_id = kwargs.get('team_id')
        if not team_id or not (current_user.is_superadmin or 
                              any(team.id == team_id for team in current_user.teams)):
            flash('You do not have access to this team.', 'error')
            return redirect(url_for('views.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({
                'status': 'error',
                'error': 'Authentication required'
            }), 401
        return f(*args, **kwargs)
    return decorated_function

def require_admin(f):
    return auth_required(['admin'])(f)

def require_superadmin(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.has_superadmin_role:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function 