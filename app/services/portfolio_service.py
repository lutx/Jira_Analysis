from app.database import get_db
from typing import Dict, List, Optional, Any
import logging
from datetime import datetime
from app.extensions import cache, db
from app.models import (
    Portfolio, 
    Project, 
    portfolio_projects, 
    User, 
    Role,
    ProjectAssignment
)

logger = logging.getLogger(__name__)

def get_all_portfolios() -> List[Dict[str, Any]]:
    """Pobierz wszystkie portfolia."""
    try:
        db = get_db()
        portfolios = db.execute('''
            SELECT p.*, 
                   COUNT(DISTINCT pp.project_key) as project_count,
                   COUNT(DISTINCT w.user_id) as users_count,
                   SUM(w.time_spent) as total_time
            FROM portfolios p
            LEFT JOIN portfolio_projects pp ON p.id = pp.portfolio_id
            LEFT JOIN worklogs w ON pp.project_key = w.project_key
            WHERE p.status = 'active'
            GROUP BY p.id
            ORDER BY p.created_at DESC
        ''').fetchall()
        
        return [dict(portfolio) for portfolio in portfolios]
    except Exception as e:
        logger.error(f"Error getting portfolios: {str(e)}")
        return []

def get_portfolio(portfolio_id: int) -> Optional[Dict[str, Any]]:
    """Pobierz szczegóły portfolio."""
    try:
        db = get_db()
        portfolio = db.execute('''
            SELECT p.*, 
                   COUNT(DISTINCT pp.project_key) as project_count,
                   COUNT(DISTINCT w.user_id) as users_count,
                   SUM(w.time_spent) as total_time
            FROM portfolios p
            LEFT JOIN portfolio_projects pp ON p.id = pp.portfolio_id
            LEFT JOIN worklogs w ON pp.project_key = w.project_key
            WHERE p.id = ?
            GROUP BY p.id
        ''', (portfolio_id,)).fetchone()
        
        if portfolio:
            return dict(portfolio)
        return None
    except Exception as e:
        logger.error(f"Error getting portfolio {portfolio_id}: {str(e)}")
        return None

def create_portfolio(data: Dict[str, Any]) -> Portfolio:
    """Create new portfolio."""
    portfolio = Portfolio(
        name=data['name'],
        description=data.get('description'),
        client_name=data.get('client_name')
    )
    db.session.add(portfolio)
    db.session.commit()
    return portfolio

def update_portfolio(portfolio_id: int, data: Dict[str, Any]) -> bool:
    """Aktualizuj portfolio."""
    try:
        if not data.get('name'):
            raise ValueError("Portfolio name is required")
            
        db = get_db()
        db.execute('''
            UPDATE portfolios 
            SET name = ?, description = ?, client_name = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (data['name'], data.get('description'), data.get('client_name'), portfolio_id))
        
        db.commit()
        return True
    except Exception as e:
        logger.error(f"Error updating portfolio {portfolio_id}: {str(e)}")
        db.rollback()
        return False

def add_project_to_portfolio(portfolio_id: int, project_key: str, assigned_by: str) -> bool:
    """Dodaj projekt do portfolio."""
    try:
        if not project_key:
            raise ValueError("Project key is required")
            
        db = get_db()
        
        # Sprawdź czy projekt już nie istnieje w portfolio
        existing = db.execute('''
            SELECT 1 FROM portfolio_projects 
            WHERE portfolio_id = ? AND project_key = ?
        ''', (portfolio_id, project_key)).fetchone()
        
        if existing:
            raise ValueError("Project already exists in portfolio")
            
        db.execute('''
            INSERT INTO portfolio_projects (portfolio_id, project_key, assigned_by)
            VALUES (?, ?, ?)
        ''', (portfolio_id, project_key, assigned_by))
        
        db.commit()
        return True
    except Exception as e:
        logger.error(f"Error adding project {project_key} to portfolio {portfolio_id}: {str(e)}")
        db.rollback()
        return False

def remove_project_from_portfolio(portfolio_id: int, project_key: str) -> bool:
    """Usuń projekt z portfolio."""
    try:
        db = get_db()
        db.execute('''
            DELETE FROM portfolio_projects 
            WHERE portfolio_id = ? AND project_key = ?
        ''', (portfolio_id, project_key))
        
        db.commit()
        return True
    except Exception as e:
        logger.error(f"Error removing project {project_key} from portfolio {portfolio_id}: {str(e)}")
        db.rollback()
        return False

@cache.memoize(timeout=300)
def get_portfolio_stats(portfolio_id: int) -> Dict[str, Any]:
    """Pobierz statystyki portfolio (z cache)."""
    try:
        db = get_db()
        stats = db.execute('''
            SELECT 
                COUNT(DISTINCT pp.project_key) as total_projects,
                COUNT(DISTINCT w.user_id) as total_users,
                COUNT(DISTINCT w.issue_key) as total_issues,
                SUM(w.time_spent) as total_time,
                AVG(w.time_spent) as avg_time_per_issue
            FROM portfolios p
            LEFT JOIN portfolio_projects pp ON p.id = pp.portfolio_id
            LEFT JOIN worklogs w ON pp.project_key = w.project_key
            WHERE p.id = ?
            GROUP BY p.id
        ''', (portfolio_id,)).fetchone()
        
        if stats:
            return dict(stats)
        return {
            'total_projects': 0,
            'total_users': 0,
            'total_issues': 0,
            'total_time': 0,
            'avg_time_per_issue': 0
        }
    except Exception as e:
        logger.error(f"Error getting portfolio stats {portfolio_id}: {str(e)}")
        return {
            'total_projects': 0,
            'total_users': 0,
            'total_issues': 0,
            'total_time': 0,
            'avg_time_per_issue': 0
        }

def get_portfolio_projects(portfolio_id: int) -> List[Dict[str, Any]]:
    """Pobierz projekty z portfolio."""
    try:
        db = get_db()
        projects = db.execute('''
            SELECT pp.*, 
                   COUNT(DISTINCT w.user_id) as users_count,
                   COUNT(DISTINCT w.issue_key) as issues_count,
                   SUM(w.time_spent) as total_time
            FROM portfolio_projects pp
            LEFT JOIN worklogs w ON pp.project_key = w.project_key
            WHERE pp.portfolio_id = ?
            GROUP BY pp.id
            ORDER BY pp.name
        ''', (portfolio_id,)).fetchall()
        
        return [dict(project) for project in projects]
    except Exception as e:
        logger.error(f"Error getting portfolio projects {portfolio_id}: {str(e)}")
        return []

def update_project_status(portfolio_id: int, project_key: str, status: str) -> bool:
    """Aktualizuj status projektu w portfolio."""
    try:
        db = get_db()
        db.execute('''
            UPDATE portfolio_projects 
            SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE portfolio_id = ? AND project_key = ?
        ''', (status, portfolio_id, project_key))
        
        db.commit()
        return True
    except Exception as e:
        logger.error(f"Error updating project status {project_key}: {str(e)}")
        db.rollback()
        return False

def assign_user_to_project(
    user_id: int,
    project_id: int,
    portfolio_id: int,
    role_id: int,
    planned_hours: float,
    month: datetime
) -> ProjectAssignment:
    """Assign user to project with planned hours."""
    assignment = ProjectAssignment(
        user_id=user_id,
        project_id=project_id,
        portfolio_id=portfolio_id,
        role_id=role_id,
        planned_hours=planned_hours,
        month=month
    )
    db.session.add(assignment)
    db.session.commit()
    return assignment

def get_portfolio_stats(portfolio_id: int, month: datetime) -> Dict[str, Any]:
    """Get portfolio statistics including planned vs actual hours."""
    # Implementation...

# Dodatkowe funkcje dla obsługi portfolio... 