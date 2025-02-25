from flask import current_app, jsonify, Response, redirect, url_for, session
from typing import Tuple, Dict, Any, Union, Optional
from datetime import datetime, timedelta, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from app.utils.db import get_db
from app.extensions import jwt, db
import logging
from app.models import User, Role, TokenBlocklist
from flask_jwt_extended import create_access_token, create_refresh_token
from flask_login import login_user
from app.exceptions import AuthenticationError, ValidationError

logger = logging.getLogger(__name__)

def hash_password(password: str) -> str:
    """Hash password using werkzeug security."""
    return generate_password_hash(password)

def verify_password(password: str, password_hash: str) -> bool:
    """Verify password against hash."""
    return check_password_hash(password_hash, password)

def login(username: str, password: str) -> dict:
    """Authenticate user and return token."""
    try:
        user = User.query.filter_by(username=username).first()
        
        if not user or not verify_password(password, user.password_hash):
            raise AuthenticationError("Invalid username or password")
            
        if not user.is_active:
            raise AuthenticationError("Account is disabled")
            
        return {
            'token': create_token(user),
            'user': user.to_dict()
        }
        
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise

def register(data: dict) -> User:
    """Register a new user."""
    try:
        # Validate required fields
        required_fields = ['username', 'email', 'password']
        for field in required_fields:
            if field not in data:
                raise ValidationError(f"Missing required field: {field}")
                
        # Check if user already exists
        if User.query.filter_by(username=data['username']).first():
            raise ValidationError("Username already exists")
            
        if User.query.filter_by(email=data['email']).first():
            raise ValidationError("Email already exists")
            
        # Create new user
        user = User(
            username=data['username'],
            email=data['email'],
            display_name=data.get('display_name', ''),
            is_active=True
        )
        user.set_password(data['password'])
        
        db.session.add(user)
        db.session.commit()
        
        return user
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Registration error: {str(e)}")
        if isinstance(e, ValidationError):
            raise
        raise ValidationError(str(e))

def create_token(user_data: Dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Tworzy token JWT.
    
    Args:
        user_data (Dict): Dane użytkownika do zapisania w tokenie
        expires_delta (timedelta, optional): Czas ważności tokenu
        
    Returns:
        str: Token JWT
    """
    if expires_delta is None:
        expires_delta = timedelta(days=1)
        
    exp = datetime.utcnow() + expires_delta
    
    to_encode = {
        "exp": exp,
        **user_data
    }
    
    return jwt.encode(to_encode, current_app.config['SECRET_KEY'], algorithm='HS256')

def verify_token(token: str) -> User:
    """Verify JWT token and return user."""
    try:
        payload = jwt.decode(
            token,
            current_app.config['SECRET_KEY'],
            algorithms=['HS256']
        )
        user = User.query.get(payload['sub'])
        if not user:
            raise AuthenticationError("User not found")
        return user
    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Token has expired")
    except jwt.InvalidTokenError:
        raise AuthenticationError("Invalid token")
    except Exception as e:
        logger.error(f"Token verification error: {str(e)}")
        raise AuthenticationError("Token verification failed")

def authenticate_user(email: str, password: str) -> dict:
    """Authenticate user and return user data."""
    try:
        user = User.query.filter_by(email=email).first()
        
        if not user or not user.check_password(password):
            logger.warning(f"Failed login attempt for email: {email}")
            return None
            
        if not user.is_active:
            logger.warning(f"Inactive user attempted login: {email}")
            return None
            
        login_user(user)
        return user.to_dict()
        
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        return None

def revoke_token(jti: str, user_name: str):
    """Revoke a token."""
    try:
        token = TokenBlocklist(jti=jti, revoked_by=user_name)
        db.session.add(token)
        db.session.commit()
        return True
    except Exception as e:
        logger.error(f"Error revoking token: {str(e)}")
        db.session.rollback()
        return False

def create_user(email: str, password: str, display_name: str = None) -> User:
    """Create a new user."""
    try:
        user = User(
            email=email,
            username=email,  # Using email as username
            display_name=display_name or email
        )
        user.set_password(password)
        
        # Add default user role
        user_role = Role.query.filter_by(name='user').first()
        if user_role:
            user.roles.append(user_role)
            
        db.session.add(user)
        db.session.commit()
        
        return user
        
    except Exception as e:
        logger.error(f"Error creating user: {str(e)}")
        db.session.rollback()
        raise

def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    """Pobiera użytkownika po nazwie."""
    try:
        db = get_db()
        user = db.execute(
            'SELECT u.*, GROUP_CONCAT(ur.role_name) as roles '
            'FROM users u '
            'LEFT JOIN user_roles ur ON u.id = ur.user_id '
            'WHERE u.username = ? '
            'GROUP BY u.id',
            (username,)
        ).fetchone()
        
        if user:
            return dict(user)
        return None
    except Exception as e:
        logger.error(f"Error getting user {username}: {str(e)}")
        return None

def update_user_password(user_id: int, new_password: str) -> bool:
    """Aktualizuje hasło użytkownika."""
    try:
        db = get_db()
        db.execute(
            'UPDATE users SET password_hash = ? WHERE id = ?',
            (generate_password_hash(new_password), user_id)
        )
        db.commit()
        return True
    except Exception as e:
        logger.error(f"Error updating password for user {user_id}: {str(e)}")
        db.rollback()
        return False

def is_password_valid(password: str) -> bool:
    """Sprawdza czy hasło spełnia wymagania bezpieczeństwa."""
    if len(password) < 8:
        return False
    if not any(c.isupper() for c in password):
        return False
    if not any(c.islower() for c in password):
        return False
    if not any(c.isdigit() for c in password):
        return False
    return True

@jwt.token_in_blocklist_loader
def check_if_token_revoked(jwt_header, jwt_payload: dict) -> bool:
    """Check if token is revoked."""
    jti = jwt_payload["jti"]
    token = TokenBlocklist.query.filter_by(jti=jti).first()
    return token is not None

def create_superadmin(username='admin', password='admin123', email='admin@example.com'):
    """Create a superadmin user."""
    try:
        # Check if superadmin already exists
        if User.query.filter_by(username=username).first():
            logger.info("Superadmin already exists")
            return False

        # Create superadmin role if it doesn't exist
        superadmin_role = Role.query.filter_by(name='superadmin').first()
        if not superadmin_role:
            superadmin_role = Role(
                name='superadmin',
                description='Super Administrator',
                permissions=['admin', 'manage_users', 'manage_roles', 'manage_settings']
            )
            db.session.add(superadmin_role)

        # Create admin role if it doesn't exist
        admin_role = Role.query.filter_by(name='admin').first()
        if not admin_role:
            admin_role = Role(
                name='admin',
                description='Administrator',
                permissions=['manage_users', 'manage_projects', 'manage_reports']
            )
            db.session.add(admin_role)

        # Create superadmin user
        superadmin = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            is_active=True,
            is_superadmin=True
        )
        
        # Add roles to superadmin
        superadmin.roles.append(superadmin_role)
        superadmin.roles.append(admin_role)
        
        db.session.add(superadmin)
        db.session.commit()
        
        logger.info(f"Superadmin user '{username}' created successfully")
        return True
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating superadmin: {str(e)}")
        raise