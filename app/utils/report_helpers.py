from typing import Dict, Any
from datetime import datetime, timedelta

def format_workload_data(workload: Dict[str, Any]) -> Dict[str, Any]:
    """Formatuje dane raportu obciążenia."""
    formatted = {
        'users': {},
        'expected_hours': workload['expected_hours'],
        'total_hours': 0,
        'avg_workload': 0
    }
    
    for user, data in workload['users'].items():
        formatted['users'][user] = {
            'hours': data['hours'],
            'percentage': data['percentage'],
            'status': get_workload_status(data['percentage'])
        }
        formatted['total_hours'] += data['hours']
    
    if workload['users']:
        formatted['avg_workload'] = sum(u['percentage'] for u in formatted['users'].values()) / len(workload['users'])
    
    return formatted

def format_activity_data(activity: Dict[str, Any]) -> Dict[str, Any]:
    """Formatuje dane raportu aktywności."""
    formatted = {
        'daily_activity': {},
        'total_hours': activity['total_hours'],
        'total_tasks': activity['total_tasks'],
        'avg_daily_hours': activity['avg_daily_hours'],
        'trend': calculate_activity_trend(activity['daily_activity'])
    }
    
    for date, hours in activity['daily_activity'].items():
        formatted['daily_activity'][date] = {
            'hours': hours,
            'tasks': activity['tasks'].get(date, 0),
            'status': get_activity_status(hours, activity['avg_daily_hours'])
        }
    
    return formatted

def format_efficiency_data(efficiency: Dict[str, Any]) -> Dict[str, Any]:
    """Formatuje dane raportu efektywności."""
    formatted = {
        'users': {},
        'total_hours': efficiency['total_hours'],
        'total_tasks': efficiency['total_tasks'],
        'avg_efficiency': efficiency['avg_efficiency']
    }
    
    for user, data in efficiency['users'].items():
        formatted['users'][user] = {
            'hours': data['hours'],
            'tasks': data['tasks'],
            'efficiency': data['efficiency'],
            'status': get_efficiency_status(data['efficiency'])
        }
    
    return formatted

def get_workload_status(percentage: float) -> str:
    """Zwraca status obciążenia."""
    if percentage > 100:
        return 'overloaded'
    if percentage >= 80:
        return 'optimal'
    return 'underutilized'

def get_activity_status(hours: float, avg_hours: float) -> str:
    """Zwraca status aktywności."""
    if hours > avg_hours * 1.2:
        return 'high'
    if hours < avg_hours * 0.8:
        return 'low'
    return 'normal'

def get_efficiency_status(efficiency: float) -> str:
    """Zwraca status efektywności."""
    if efficiency > 100:
        return 'excellent'
    if efficiency >= 80:
        return 'good'
    if efficiency >= 60:
        return 'average'
    return 'poor'

def calculate_activity_trend(daily_activity: Dict[str, float]) -> str:
    """Oblicza trend aktywności."""
    if not daily_activity:
        return 'stable'
        
    dates = sorted(daily_activity.keys())
    if len(dates) < 2:
        return 'stable'
        
    first_half = sum(daily_activity[d] for d in dates[:len(dates)//2])
    second_half = sum(daily_activity[d] for d in dates[len(dates)//2:])
    
    change = (second_half - first_half) / first_half * 100 if first_half > 0 else 0
    
    if change > 10:
        return 'increasing'
    if change < -10:
        return 'decreasing'
    return 'stable'

def format_member_stats(stats: Dict[str, Any]) -> Dict[str, Any]:
    """Formatuje dane statystyk członka zespołu."""
    formatted = {
        'daily_stats': {},
        'total_hours': stats['total_hours'],
        'total_tasks': stats['total_tasks'],
        'avg_daily_hours': stats['avg_daily_hours'],
        'avg_tasks_per_day': stats['avg_tasks_per_day'],
        'projects': sorted(stats['projects']),
        'trend': calculate_activity_trend(stats['daily_stats'])
    }
    
    for date, data in stats['daily_stats'].items():
        formatted['daily_stats'][date] = {
            'hours': data['hours'],
            'tasks': data['tasks'],
            'projects': sorted(data['projects']),
            'status': get_activity_status(data['hours'], stats['avg_daily_hours'])
        }
    
    return formatted

def format_project_stats(stats: Dict[str, Any]) -> Dict[str, Any]:
    """Formatuje dane statystyk projektu."""
    formatted = {
        'users': {},
        'total_hours': stats['total_hours'],
        'total_tasks': stats['total_tasks'],
        'avg_hours_per_user': stats['avg_hours_per_user']
    }
    
    for user, data in stats['users'].items():
        percentage = (data['hours'] / stats['total_hours'] * 100) if stats['total_hours'] > 0 else 0
        formatted['users'][user] = {
            'hours': data['hours'],
            'tasks': data['tasks'],
            'percentage': percentage,
            'status': get_workload_status(percentage)
        }
    
    return formatted 