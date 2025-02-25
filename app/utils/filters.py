from datetime import datetime
from typing import List, Any
from flask import Blueprint

filters_bp = Blueprint('filters', __name__)

@filters_bp.app_template_filter('format_date')
def format_date(value):
    """Format date to YYYY-MM-DD."""
    if isinstance(value, str):
        try:
            value = datetime.strptime(value, '%Y-%m-%d')
        except ValueError:
            return value
    if isinstance(value, datetime):
        return value.strftime('%Y-%m-%d')
    return value

@filters_bp.app_template_filter('format_datetime')
def format_datetime(value):
    """Format datetime to YYYY-MM-DD HH:MM:SS."""
    if isinstance(value, str):
        try:
            value = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            return value
    if isinstance(value, datetime):
        return value.strftime('%Y-%m-%d %H:%M:%S')
    return value

@filters_bp.app_template_filter('timeago')
def timeago(value):
    """Format datetime as time ago."""
    if not value:
        return ''
        
    if isinstance(value, str):
        try:
            value = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            return value
            
    now = datetime.now()
    diff = now - value
    
    if diff.days > 365:
        years = diff.days // 365
        return f"{years} year{'s' if years != 1 else ''} ago"
    if diff.days > 30:
        months = diff.days // 30
        return f"{months} month{'s' if months != 1 else ''} ago"
    if diff.days > 0:
        return f"{diff.days} day{'s' if diff.days != 1 else ''} ago"
    if diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    if diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    return "just now"

def format_duration(minutes):
    """Format duration in minutes to human readable string."""
    if not minutes:
        return '0h'
    hours = minutes // 60
    remaining_minutes = minutes % 60
    if remaining_minutes:
        return f'{hours}h {remaining_minutes}m'
    return f'{hours}h'

def has_role(user_roles: List[str], role: str) -> bool:
    """Jinja filter to check if user has a role."""
    if not user_roles:
        return False
    return role in user_roles

def to_date(date_string):
    """Konwertuje string na obiekt datetime."""
    if not date_string:
        return None
    return datetime.strptime(date_string, '%Y-%m-%d')

def register_filters(app):
    """Register custom filters with Flask app."""
    app.jinja_env.filters['datetime'] = format_datetime
    app.jinja_env.filters['date'] = format_date
    app.jinja_env.filters['duration'] = format_duration
    app.jinja_env.filters['has_role'] = has_role
    app.jinja_env.filters['to_date'] = to_date 