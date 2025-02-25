from flask import Blueprint, request, session, redirect, url_for, render_template, flash, current_app, g, jsonify, abort, make_response
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField
from wtforms.validators import DataRequired
from app.services.jira_service import get_jira_service
import logging
from werkzeug.security import check_password_hash
from app.database import get_db
from app.services.auth_service import (
    authenticate_user, create_user, verify_password,
    get_user_by_username, update_user_password,
    is_password_valid, hash_password, login, register, verify_token
)
from app.utils.decorators import auth_required
from typing import Dict, Any
from app.forms import LoginForm, UserSettingsForm
from app.utils.auth_helpers import has_role
from urllib.parse import urlparse
from app.models import User
from flask_login import login_user, logout_user, login_required, current_user
from app.extensions import db, csrf
from datetime import datetime
from flask_wtf.csrf import CSRFError, generate_csrf

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')
logger = logging.getLogger(__name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login."""
    logger.info("=== Login attempt ===")
    logger.info(f"Request host: {request.host}")
    logger.info(f"Request headers: {dict(request.headers)}")
    
    if current_user.is_authenticated:
        logger.info(f"User {current_user.username} already authenticated")
        return redirect(url_for('main.dashboard'))

    form = LoginForm()
    
    if request.method == 'POST':
        logger.info("Processing POST request")
        logger.info(f"Form data: {request.form}")
        logger.info(f"Form validation: {form.validate()}")
        logger.info(f"Form errors: {form.errors}")
        logger.info(f"CSRF token in form: {request.form.get('csrf_token')}")
        try:
            session_data = {key: session[key] for key in session.keys()} if session else {}
            logger.info(f"Session data: {session_data}")
        except Exception as e:
            logger.error(f"Error accessing session data: {str(e)}")

    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            session.permanent = True
            
            next_page = request.args.get('next')
            if not next_page or urlparse(next_page).netloc != '':
                next_page = url_for('main.dashboard')
            
            response = redirect(next_page)
            response.headers['Access-Control-Allow-Origin'] = "http://192.168.90.114:5003"
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            response.headers['Vary'] = 'Origin'
            
            # Upewnij się, że ciasteczka sesji są poprawnie ustawione
            try:
                session_id = session.sid if hasattr(session, 'sid') else ''
                if not session_id and '_id' in session:
                    session_id = session['_id']
                
                response.set_cookie(
                    'session',
                    session_id,
                    httponly=True,
                    secure=False,  # Zmień na True w produkcji
                    samesite='Lax',
                    domain=None,
                    path='/'
                )
            except Exception as e:
                logger.error(f"Error setting session cookie: {str(e)}")
            
            flash('Zalogowano pomyślnie.', 'success')
            return response
            
        flash('Nieprawidłowa nazwa użytkownika lub hasło.', 'danger')
    
    response = make_response(render_template('auth/login.html', form=form))
    response.headers['Access-Control-Allow-Origin'] = "http://192.168.90.114:5003"
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    response.headers['Vary'] = 'Origin'
    return response

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Rejestracja nowego użytkownika."""
    if current_user.is_authenticated:
        return redirect(url_for('views.dashboard'))
        
    if request.method == 'POST':
        try:
            username = request.form.get('username')
            password = request.form.get('password')
            email = request.form.get('email')
            
            if not all([username, password, email]):
                flash('Wszystkie pola są wymagane.', 'danger')
                return render_template('auth/register.html', form=FlaskForm())
                
            if not is_password_valid(password):
                flash('Hasło nie spełnia wymagań bezpieczeństwa.', 'danger')
                return render_template('auth/register.html', form=FlaskForm())
                
            user_data = {
                'username': username,
                'password': password,
                'email': email
            }
            
            if create_user(user_data):
                flash('Konto zostało utworzone. Możesz się zalogować.', 'success')
                return redirect(url_for('auth.login'))
                
            flash('Użytkownik o takiej nazwie już istnieje.', 'danger')
            
        except Exception as e:
            logger.error(f"Registration error: {str(e)}")
            flash('Wystąpił błąd podczas rejestracji.', 'danger')
            
    return render_template('auth/register.html', form=FlaskForm())

@auth_bp.route('/logout')
def logout():
    """Logout view."""
    logout_user()
    return redirect(url_for('auth.login'))

@auth_bp.route('/status')
def status():
    if current_user.is_authenticated:
        return jsonify({
            'status': 'success',
            'authenticated': True,
            'user': {
                'username': current_user.username,
                'email': current_user.email
            }
        })
    return jsonify({
        'status': 'success',
        'authenticated': False
    })

@auth_bp.route('/change-password', methods=['POST'])
@auth_required()
def change_password():
    """Zmiana hasła użytkownika."""
    try:
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        
        if not all([current_password, new_password]):
            return jsonify({'status': 'error', 'message': 'Wszystkie pola są wymagane'}), 400
            
        if not is_password_valid(new_password):
            return jsonify({'status': 'error', 'message': 'Nowe hasło nie spełnia wymagań bezpieczeństwa'}), 400
            
        user = get_user_by_username(g.user['username'])
        if not user or not verify_password(current_password, user['password_hash']):
            return jsonify({'status': 'error', 'message': 'Nieprawidłowe aktualne hasło'}), 400
            
        if update_user_password(user['id'], new_password):
            return jsonify({'status': 'success'})
            
        return jsonify({'status': 'error', 'message': 'Nie udało się zmienić hasła'}), 500
        
    except Exception as e:
        logger.error(f"Password change error: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@auth_bp.before_app_request
def load_logged_in_user():
    """Load user data before each request."""
    user_data = session.get('user')
    if user_data is None:
        g.user = None
    else:
        g.user = {
            'user_name': user_data.get('user_name'),
            'email': user_data.get('email'),
            'roles': user_data.get('roles', [])
        }

@auth_bp.errorhandler(Exception)
def handle_auth_error(error):
    """Handle authentication errors."""
    logger.error(f"Auth error: {str(error)}")
    if current_app.debug:
        raise error  # W trybie debug pokazujemy pełny traceback
    flash('An error occurred. Please try again.', 'error')
    return render_template('auth/login.html', form=LoginForm()), 500

@auth_bp.route('/check-db')
def check_db():
    """Debug endpoint to check database state."""
    if not current_app.debug:
        abort(404)
        
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Check users table
        cursor.execute('SELECT * FROM users')
        users = cursor.fetchall()
        
        # Check roles table
        cursor.execute('SELECT * FROM roles')
        roles = cursor.fetchall()
        
        return jsonify({
            'users': [dict(user) for user in users],
            'roles': [dict(role) for role in roles]
        })
        
    except Exception as e:
        logger.error(f"Database check error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/check-user/<email>')
def check_user(email):
    """Debug endpoint to check user details."""
    if not current_app.debug:
        abort(404)
        
    try:
        user = User.query.filter_by(email=email).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404
            
        return jsonify({
            'user_name': user.user_name,
            'email': user.email,
            'is_active': user.is_active,
            'roles': [role.name for role in user.roles],
            'password_hash': user.password_hash[:20] + '...'  # Pokazujemy tylko początek hasha dla bezpieczeństwa
        })
        
    except Exception as e:
        logger.error(f"Error checking user: {str(e)}")
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/debug/users')
def debug_users():
    """Debug endpoint do sprawdzenia użytkowników w bazie."""
    if not current_app.debug:
        return jsonify({"error": "Only available in debug mode"}), 403
        
    try:
        users = User.query.all()
        return jsonify({
            'users': [{
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'is_active': user.is_active,
                'is_superadmin': user.is_superadmin,
                'has_password': bool(user.password_hash),
                'roles': [role.name for role in user.roles]
            } for user in users]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@auth_bp.errorhandler(CSRFError)
def handle_csrf_error(e):
    """Handle CSRF errors."""
    logger.warning(f"CSRF error: {str(e)}")
    if request.is_json:
        return jsonify({
            'status': 'error',
            'message': 'CSRF token missing or invalid',
            'code': 'csrf_error'
        }), 400
    flash('Sesja wygasła. Proszę spróbować ponownie.', 'warning')
    return redirect(url_for('auth.login'))

@auth_bp.route('/profile')
@login_required
def profile():
    """User profile page."""
    return render_template('auth/profile.html')

@auth_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    """User account settings."""
    try:
        form = UserSettingsForm()
        
        if form.validate_on_submit():
            current_user.email = form.email.data
            current_user.display_name = form.display_name.data
            current_user.jira_username = form.jira_username.data
            current_user.jira_email = form.jira_email.data
            
            if form.password.data:
                current_user.set_password(form.password.data)
                
            db.session.commit()
            flash('Ustawienia zostały zaktualizowane.', 'success')
            return redirect(url_for('auth.settings'))
            
        elif request.method == 'GET':
            form.email.data = current_user.email
            form.display_name.data = current_user.display_name
            form.jira_username.data = current_user.jira_username
            form.jira_email.data = current_user.jira_email
            
        return render_template('auth/settings.html', form=form)
        
    except Exception as e:
        logger.error(f"Error in user settings: {str(e)}")
        flash('Wystąpił błąd podczas aktualizacji ustawień.', 'danger')
        return redirect(url_for('main.dashboard')) 