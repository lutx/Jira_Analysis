from app.database import get_db
from datetime import datetime
import logging
from calendar import monthrange

logger = logging.getLogger(__name__)

def get_all_users():
    """Pobierz wszystkich użytkowników."""
    try:
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute('''
            SELECT u.*, GROUP_CONCAT(r.name) as roles
            FROM users u
            LEFT JOIN user_roles ur ON u.username = ur.user_name
            LEFT JOIN roles r ON ur.role_id = r.id
            WHERE u.is_active = 1
            GROUP BY u.username
            ORDER BY u.username
        ''')
        
        return cursor.fetchall()
    except Exception as e:
        logger.error(f"Error getting users: {str(e)}")
        return []

def get_all_roles():
    """Pobierz wszystkie role."""
    try:
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute('SELECT * FROM roles ORDER BY name')
        return cursor.fetchall()
    except Exception as e:
        logger.error(f"Error getting roles: {str(e)}")
        return []

def get_user_assignments(username, month_year=None):
    """Pobierz przypisania użytkownika do projektów."""
    try:
        db = get_db()
        cursor = db.cursor()
        
        if not month_year:
            month_year = datetime.now().strftime('%Y-%m')
            
        cursor.execute('''
            SELECT 
                pa.*,
                p.name as portfolio_name,
                r.name as role_name
            FROM project_assignments pa
            JOIN portfolio_projects pp ON pa.project_key = pp.project_key
            JOIN portfolios p ON pp.portfolio_id = p.id
            LEFT JOIN roles r ON pa.role_id = r.id
            WHERE pa.user_name = ? AND pa.month_year = ?
        ''', (username, month_year))
        
        return cursor.fetchall()
    except Exception as e:
        logger.error(f"Error getting user assignments: {str(e)}")
        return []

def create_assignment(assignment_data):
    """Utwórz nowe przypisanie."""
    try:
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute('''
            INSERT INTO project_assignments 
            (user_name, project_key, role_id, planned_hours, month_year)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            assignment_data['user_name'],
            assignment_data['project_key'],
            assignment_data['role_id'],
            assignment_data['planned_hours'],
            assignment_data['month_year']
        ))
        
        db.commit()
        return True
    except Exception as e:
        logger.error(f"Error creating assignment: {str(e)}")
        db.rollback()
        return False

def update_user_availability(username, month_year, availability_data):
    """Aktualizuj dostępność użytkownika."""
    try:
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO user_availability 
            (user_name, month_year, working_days, holidays, leave_days)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            username,
            month_year,
            availability_data['working_days'],
            availability_data['holidays'],
            availability_data['leave_days']
        ))
        
        db.commit()
        return True
    except Exception as e:
        logger.error(f"Error updating availability: {str(e)}")
        db.rollback()
        return False

def get_project_assignments(project_key, month_year=None):
    """Pobierz przypisania do projektu."""
    try:
        db = get_db()
        cursor = db.cursor()
        
        if not month_year:
            month_year = datetime.now().strftime('%Y-%m')
            
        cursor.execute('''
            SELECT 
                pa.*,
                u.email,
                r.name as role_name,
                (SELECT SUM(w.time_spent) 
                 FROM worklogs w 
                 WHERE w.user_id = (SELECT id FROM users WHERE username = pa.user_name)
                 AND w.project_key = pa.project_key
                 AND strftime('%Y-%m', w.started) = ?) as actual_hours
            FROM project_assignments pa
            JOIN users u ON pa.user_name = u.username
            JOIN roles r ON pa.role_id = r.id
            WHERE pa.project_key = ? AND pa.month_year = ?
        ''', (month_year, project_key, month_year))
        
        return cursor.fetchall()
    except Exception as e:
        logger.error(f"Error getting project assignments: {str(e)}")
        return []

def get_role_assignments(role_id, month_year=None):
    """Pobierz przypisania dla roli."""
    try:
        db = get_db()
        cursor = db.cursor()
        
        if not month_year:
            month_year = datetime.now().strftime('%Y-%m')
            
        cursor.execute('''
            SELECT 
                pa.*,
                u.email,
                p.name as portfolio_name,
                (SELECT SUM(w.time_spent) 
                 FROM worklogs w 
                 WHERE w.user_id = (SELECT id FROM users WHERE username = pa.user_name)
                 AND w.project_key = pa.project_key
                 AND strftime('%Y-%m', w.started) = ?) as actual_hours
            FROM project_assignments pa
            JOIN users u ON pa.user_name = u.username
            JOIN portfolio_projects pp ON pa.project_key = pp.project_key
            JOIN portfolios p ON pp.portfolio_id = p.id
            WHERE pa.role_id = ? AND pa.month_year = ?
        ''', (month_year, role_id, month_year))
        
        return cursor.fetchall()
    except Exception as e:
        logger.error(f"Error getting role assignments: {str(e)}")
        return [] 