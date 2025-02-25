from app.extensions import db
from flask import current_app
from app.models.user import User
from app.models.role import Role
from app.models.worklog import Worklog
from typing import Dict, Any, Optional
import logging
from sqlalchemy import func, distinct
from flask import current_app
from werkzeug.security import generate_password_hash
from app.models.project import Project
from app.models.setting import Setting
from app.models.jira_config import JiraConfig
import os

logger = logging.getLogger(__name__)

def get_users_count() -> int:
    """Get total users count."""
    try:
        return User.query.count()
    except Exception as e:
        logger.error(f"Error getting users count: {str(e)}")
        return 0

def get_active_users_count() -> int:
    """Get active users count."""
    try:
        return User.query.filter_by(is_active=True).count()
    except Exception as e:
        logger.error(f"Error getting active users count: {str(e)}")
        return 0

def get_total_worklogs() -> int:
    """Get total worklogs count."""
    try:
        return Worklog.query.count()
    except Exception as e:
        logger.error(f"Error getting total worklogs: {str(e)}")
        return 0

def get_total_projects() -> int:
    """Get total number of projects."""
    try:
        return Project.query.count()
    except Exception as e:
        logger.error(f"Error getting total projects: {str(e)}")
        return 0

def is_jira_connected() -> bool:
    """Check if Jira is connected."""
    from app.services.jira_service import get_jira_service
    try:
        jira = get_jira_service()
        # Zmiana: sprawdzamy czy jira istnieje i ma atrybut is_connected
        return bool(jira and hasattr(jira, 'is_connected') and jira.is_connected)
    except Exception as e:
        logger.error(f"Error checking JIRA connection: {str(e)}")
        return False

def get_last_sync_time() -> Optional[str]:
    """Get last sync time."""
    try:
        last_worklog = Worklog.query.order_by(Worklog.updated_at.desc()).first()
        return last_worklog.updated_at.strftime("%Y-%m-%d %H:%M:%S") if last_worklog else None
    except Exception as e:
        logger.error(f"Error getting last sync time: {str(e)}")
        return None

def get_system_status() -> dict:
    """Pobiera status systemu."""
    return {
        'database': check_database_status(),
        'cache': check_cache_status(),
        'jira': is_jira_connected(),
        'disk_space': check_disk_space()
    }

def check_database_status() -> bool:
    """Sprawdza status bazy danych."""
    try:
        # Używamy SQLAlchemy zamiast raw SQL
        result = db.session.execute('SELECT 1').scalar()
        return result == 1
    except Exception:
        return False

def check_cache_status() -> bool:
    """Sprawdza status cache."""
    try:
        from app.extensions import cache
        return cache.get('test_key') is not None
    except Exception:
        return False

def check_disk_space() -> bool:
    """Sprawdza dostępną przestrzeń dyskową."""
    try:
        import psutil
        disk = psutil.disk_usage('/')
        return disk.percent < 90  # Zwraca False jeśli zajęte jest więcej niż 90%
    except Exception:
        return False

def get_system_logs() -> list:
    """Pobiera logi systemowe."""
    try:
        log_files = ['app.log', 'error.log']
        logs = []
        
        for log_file in log_files:
            file_path = os.path.join(current_app.instance_path, 'logs', log_file)
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    # Pobierz ostatnie 100 linii
                    lines = f.readlines()[-100:]
                    logs.extend(lines)
        
        return logs
        
    except Exception as e:
        logger.error(f"Error getting system logs: {str(e)}")
        return []

def save_app_settings(settings: Dict[str, Any]) -> bool:
    """Save application settings."""
    try:
        logger.info(f"Attempting to save settings: {settings}")
        
        # Aktualizuj konfigurację Jira
        jira_config = JiraConfig.query.first()
        if not jira_config:
            logger.info("Creating new JiraConfig")
            jira_config = JiraConfig()
            db.session.add(jira_config)
        
        # Aktualizuj pola
        jira_config.url = settings.get('JIRA_URL')
        jira_config.username = settings.get('JIRA_USER')
        if settings.get('JIRA_TOKEN'):
            jira_config.api_token = settings.get('JIRA_TOKEN')
        jira_config.is_active = True
        
        # Aktualizuj konfigurację aplikacji
        current_app.config.update(settings)
        
        db.session.commit()
        logger.info("Settings saved successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error saving settings: {str(e)}", exc_info=True)
        db.session.rollback()
        return False

def save_user(user_data: dict) -> bool:
    """Zapisz dane użytkownika."""
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Dodaj użytkownika
        cursor.execute(
            'INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)',
            (user_data['username'], user_data['email'], 
             generate_password_hash(user_data['password']))
        )
        
        # Dodaj role
        for role in user_data['roles']:
            cursor.execute(
                'INSERT INTO user_roles (user_name, role_id) VALUES (?, ?)',
                (user_data['username'], role)
            )
            
        db.commit()
        return True
    except Exception as e:
        logger.error(f"Error saving user: {str(e)}")
        return False

def save_role(role_data: dict) -> bool:
    """Zapisz dane roli."""
    try:
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute(
            '''INSERT INTO roles (
                name, description, permissions, created_by, 
                is_active, is_system
            ) VALUES (?, ?, ?, ?, ?, ?)''',
            (
                role_data['name'],
                role_data['description'],
                ','.join(role_data['permissions']),
                'admin',  # Domyślnie utworzone przez admina
                True,    # Domyślnie aktywna
                False    # Domyślnie nie systemowa
            )
        )
        
        db.commit()
        return True
    except Exception as e:
        logger.error(f"Error saving role: {str(e)}")
        return False

def is_username_taken(username: str) -> bool:
    """Sprawdza czy nazwa użytkownika jest już zajęta."""
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute('SELECT 1 FROM users WHERE username = ?', (username,))
        return cursor.fetchone() is not None
    except Exception as e:
        logger.error(f"Error checking username: {str(e)}")
        return True  # W razie błędu zakładamy, że nazwa jest zajęta

def is_role_name_taken(name: str) -> bool:
    """Sprawdza czy nazwa roli jest już zajęta."""
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute('SELECT 1 FROM roles WHERE name = ?', (name,))
        return cursor.fetchone() is not None
    except Exception as e:
        logger.error(f"Error checking role name: {str(e)}")
        return True  # W razie błędu zakładamy, że nazwa jest zajęta

def get_all_users() -> list:
    """Pobiera listę wszystkich użytkowników."""
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute('''
            SELECT u.*, GROUP_CONCAT(r.name) as roles
            FROM users u
            LEFT JOIN user_roles ur ON u.username = ur.user_name
            LEFT JOIN roles r ON ur.role_id = r.id
            GROUP BY u.id
        ''')
        return cursor.fetchall()
    except Exception as e:
        logger.error(f"Error getting users: {str(e)}")
        return []

def get_all_roles() -> list:
    """Pobiera listę wszystkich ról."""
    try:
        roles = Role.query.order_by(Role.name).all()
        return roles
    except Exception as e:
        logger.error(f"Error getting roles: {str(e)}")
        return []

def delete_user_by_username(username: str) -> bool:
    """Usuń użytkownika o podanej nazwie."""
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Najpierw usuń powiązane role
        cursor.execute('DELETE FROM user_roles WHERE user_name = ?', (username,))
        
        # Następnie usuń użytkownika
        cursor.execute('DELETE FROM users WHERE username = ?', (username,))
        
        db.commit()
        return True
    except Exception as e:
        logger.error(f"Error deleting user: {str(e)}")
        return False

def delete_role_by_name(name: str) -> bool:
    """Usuń rolę o podanej nazwie."""
    try:
        # Sprawdź czy to nie jest rola systemowa
        role = Role.query.filter_by(name=name).first()
        if not role:
            logger.error(f"Role not found: {name}")
            return False
            
        if role.name in ['superadmin', 'admin', 'User']:
            logger.error(f"Cannot delete system role: {name}")
            return False
            
        # Usuń rolę
        db.session.delete(role)
        db.session.commit()
        logger.info(f"Successfully deleted role: {name}")
        return True
        
    except Exception as e:
        logger.error(f"Error deleting role: {str(e)}")
        db.session.rollback()
        return False

def get_roles():
    """Get all roles."""
    try:
        roles = Role.query.all()
        return roles
    except Exception as e:
        logger.error(f"Error getting roles: {str(e)}")
        return []

def get_role_by_id(role_id):
    """Get role by ID."""
    try:
        role = Role.query.get(role_id)
        return role
    except Exception as e:
        logger.error(f"Error getting role: {str(e)}")
        return None

def create_new_role(name: str, description: str = None, permissions: list = None) -> Optional[Role]:
    """Create new role."""
    try:
        role = Role(
            name=name,
            description=description,
            permissions=permissions
        )
        db.session.add(role)
        db.session.commit()
        return role
    except Exception as e:
        logger.error(f"Error creating role: {str(e)}")
        db.session.rollback()
        return None

def update_role(role_id: int, name: str = None, description: str = None, permissions: list = None) -> Optional[Role]:
    """Update role."""
    try:
        role = Role.query.get(role_id)
        if not role:
            return None
            
        # Nie pozwól na edycję ról systemowych
        if role.name in ['superadmin', 'admin', 'User']:
            raise ValueError("Cannot edit system roles")
            
        if name:
            # Sprawdź czy nazwa nie jest już zajęta przez inną rolę
            existing_role = Role.query.filter(Role.name == name, Role.id != role_id).first()
            if existing_role:
                raise ValueError(f"Role with name {name} already exists")
            role.name = name
            
        if description is not None:
            role.description = description
            
        if permissions is not None:
            role.permissions = permissions
            
        db.session.commit()
        return role
    except Exception as e:
        logger.error(f"Error updating role: {str(e)}")
        db.session.rollback()
        return None

def delete_role(role_id):
    """Delete role."""
    try:
        role = Role.query.get(role_id)
        if role:
            db.session.delete(role)
            db.session.commit()
            return True
        return False
    except Exception as e:
        logger.error(f"Error deleting role: {str(e)}")
        db.session.rollback()
        return False

def create_initial_admin():
    """Tworzy początkowego administratora."""
    try:
        # Sprawdź czy admin już istnieje
        admin = User.query.filter_by(username='admin').first()
        if admin:
            return

        # Utwórz rolę admin jeśli nie istnieje
        admin_role = Role.query.filter_by(name='admin').first()
        if not admin_role:
            admin_role = Role(
                name='admin',
                description='Administrator systemu',
                permissions=['all']
            )
            db.session.add(admin_role)

        # Utwórz admina
        admin = User(
            username='admin',
            email='admin@example.com',
            display_name='Administrator',
            is_active=True
        )
        admin.set_password('admin123')
        admin.roles.append(admin_role)
        
        db.session.add(admin)
        db.session.commit()
        logger.info("Created initial admin user")
    except Exception as e:
        logger.error(f"Error creating initial admin: {str(e)}")
        db.session.rollback()

def get_users():
    """Pobiera listę użytkowników."""
    try:
        return User.query.all()
    except Exception as e:
        logger.error(f"Error getting users: {str(e)}")
        return []

def get_user_by_id(user_id):
    """Pobiera użytkownika po ID."""
    try:
        return User.query.get(user_id)
    except Exception as e:
        logger.error(f"Error getting user {user_id}: {str(e)}")
        return None

def create_user(user_data):
    """Tworzy nowego użytkownika."""
    try:
        user = User(
            username=user_data['username'],
            email=user_data['email'],
            display_name=user_data.get('display_name'),
            is_active=user_data.get('is_active', True)
        )
        user.set_password(user_data['password'])
        
        # Dodaj role z formularza, jeśli są
        if 'roles' in user_data:
            roles = Role.query.filter(Role.id.in_(user_data['roles'])).all()
            user.roles.extend(roles)
        
        # Upewnij się, że użytkownik ma domyślną rolę
        if not user.roles:
            default_role = Role.get_or_create_default_role()
            if default_role:
                user.add_role(default_role)
            
        db.session.add(user)
        db.session.commit()
        return True
    except Exception as e:
        logger.error(f"Error creating user: {str(e)}")
        db.session.rollback()
        return False

def delete_user(user_id):
    """Usuwa użytkownika."""
    try:
        user = User.query.get(user_id)
        if user and not user.is_superadmin:
            db.session.delete(user)
            db.session.commit()
            return True
        return False
    except Exception as e:
        logger.error(f"Error deleting user: {str(e)}")
        db.session.rollback()
        return False

def get_dashboard_stats():
    """Get admin dashboard statistics."""
    try:
        total_users = User.query.count()
        total_projects = Project.query.count()
        total_worklogs = Worklog.query.count()
        
        # Pobierz statystyki worklogów
        recent_worklogs = (Worklog.query
                          .order_by(Worklog.created_at.desc())
                          .limit(5)
                          .all())
        
        # Pobierz statystyki projektów
        project_stats = db.session.query(
            Worklog.project_key,
            db.func.count(Worklog.id).label('total_logs'),
            db.func.sum(Worklog.time_spent).label('total_time')
        ).group_by(Worklog.project_key).all()
        
        return {
            'total_users': total_users,
            'total_projects': total_projects,
            'total_worklogs': total_worklogs,
            'recent_worklogs': recent_worklogs,
            'project_stats': project_stats
        }
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {str(e)}")
        return {
            'error': str(e),
            'total_users': 0,
            'total_projects': 0,
            'total_worklogs': 0,
            'recent_worklogs': [],
            'project_stats': []
        }

def get_role(role_id):
    """Get role by ID."""
    try:
        role = Role.query.get(role_id)
        return role
    except Exception as e:
        logger.error(f"Error getting role: {str(e)}")
        return None

def get_admin_notifications():
    """Get admin notifications."""
    try:
        notifications = []
        
        # Check JIRA connection
        jira_config = JiraConfig.query.filter_by(is_active=True).first()
        if not jira_config:
            notifications.append({
                'type': 'warning',
                'message': 'JIRA nie jest skonfigurowana'
            })
            
        # Check inactive users
        inactive_users = User.query.filter_by(is_active=False).count()
        if inactive_users > 0:
            notifications.append({
                'type': 'info',
                'message': f'Masz {inactive_users} nieaktywnych użytkowników'
            })
            
        return notifications
    except Exception as e:
        logger.error(f"Error getting admin notifications: {str(e)}")
        return [] 