import pytest
from datetime import datetime
from app.utils.report_helpers import (
    format_member_stats,
    format_project_stats,
    calculate_activity_trend,
    get_activity_status,
    get_workload_status
)

def test_format_member_stats():
    """Test formatowania statystyk członka zespołu."""
    test_stats = {
        'daily_stats': {
            '2023-01-01': {
                'hours': 8.0,
                'tasks': 3,
                'projects': ['PROJ-1', 'PROJ-2']
            },
            '2023-01-02': {
                'hours': 6.0,
                'tasks': 2,
                'projects': ['PROJ-1']
            }
        },
        'total_hours': 14.0,
        'total_tasks': 5,
        'avg_daily_hours': 7.0,
        'avg_tasks_per_day': 2.5,
        'projects': ['PROJ-2', 'PROJ-1']
    }
    
    formatted = format_member_stats(test_stats)
    
    assert formatted['total_hours'] == 14.0
    assert formatted['total_tasks'] == 5
    assert formatted['avg_daily_hours'] == 7.0
    assert formatted['avg_tasks_per_day'] == 2.5
    assert formatted['projects'] == ['PROJ-1', 'PROJ-2']  # Posortowane
    assert 'trend' in formatted
    assert len(formatted['daily_stats']) == 2
    assert 'status' in formatted['daily_stats']['2023-01-01']

def test_format_project_stats():
    """Test formatowania statystyk projektu."""
    test_stats = {
        'users': {
            'user1': {
                'hours': 16.0,
                'tasks': 5
            },
            'user2': {
                'hours': 8.0,
                'tasks': 3
            }
        },
        'total_hours': 24.0,
        'total_tasks': 8,
        'avg_hours_per_user': 12.0
    }
    
    formatted = format_project_stats(test_stats)
    
    assert formatted['total_hours'] == 24.0
    assert formatted['total_tasks'] == 8
    assert formatted['avg_hours_per_user'] == 12.0
    assert len(formatted['users']) == 2
    assert formatted['users']['user1']['percentage'] == pytest.approx(66.67, 0.01)
    assert 'status' in formatted['users']['user1']

def test_calculate_activity_trend():
    """Test obliczania trendu aktywności."""
    # Trend rosnący
    increasing = {
        '2023-01-01': 5.0,
        '2023-01-02': 6.0,
        '2023-01-03': 7.0,
        '2023-01-04': 8.0
    }
    assert calculate_activity_trend(increasing) == 'increasing'
    
    # Trend malejący
    decreasing = {
        '2023-01-01': 8.0,
        '2023-01-02': 7.0,
        '2023-01-03': 6.0,
        '2023-01-04': 5.0
    }
    assert calculate_activity_trend(decreasing) == 'decreasing'
    
    # Trend stabilny
    stable = {
        '2023-01-01': 6.0,
        '2023-01-02': 6.0,
        '2023-01-03': 6.0,
        '2023-01-04': 6.0
    }
    assert calculate_activity_trend(stable) == 'stable'
    
    # Pusty słownik
    assert calculate_activity_trend({}) == 'stable'

def test_get_activity_status():
    """Test określania statusu aktywności."""
    avg_hours = 8.0
    
    assert get_activity_status(10.0, avg_hours) == 'high'  # > 120%
    assert get_activity_status(8.0, avg_hours) == 'normal'  # 100%
    assert get_activity_status(6.0, avg_hours) == 'low'  # < 80%

def test_get_workload_status():
    """Test określania statusu obciążenia."""
    assert get_workload_status(120.0) == 'overloaded'  # > 100%
    assert get_workload_status(90.0) == 'optimal'  # >= 80%
    assert get_workload_status(70.0) == 'underutilized'  # < 80% 