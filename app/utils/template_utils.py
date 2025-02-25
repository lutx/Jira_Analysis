from flask import g
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def current_user() -> Dict[str, Any]:
    """Returns current user data for templates."""
    if hasattr(g, 'user'):
        user_data = {
            'is_authenticated': True,
            'user_name': g.user.get('user_name'),
            'email': g.user.get('email'),
            'roles': g.user.get('roles', [])
        }
        logger.debug(f"Current user data: {user_data}")
        return user_data
        
    logger.debug("No user data found")
    return {
        'is_authenticated': False,
        'user_name': None,
        'email': None,
        'roles': []
    }

def format_date(date: datetime, format: str = '%Y-%m-%d') -> str:
    """Format date for templates."""
    if not date:
        return ''
    return date.strftime(format)

def format_hours(hours: float) -> str:
    """Format hours for templates."""
    if not hours:
        return '0h'
    return f"{hours:.1f}h"

def get_user_roles(user: Optional[Dict[str, Any]] = None) -> List[str]:
    """Get user roles."""
    if user is None:
        user = getattr(g, 'user', {})
    return user.get('roles', [])

def get_user_stats(user: Dict[str, Any]) -> Dict[str, Any]:
    """Get dashboard statistics for user."""
    try:
        from app.services.dashboard_service import get_dashboard_stats
        return get_dashboard_stats(user['user_name'])
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {str(e)}")
        return {
            'stats': {},
            'activity_data': [],
            'activity_labels': [],
            'status_data': [],
            'status_labels': [],
            'activities': []
        } 