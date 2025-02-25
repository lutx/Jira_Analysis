import pytest
from app.models import User, Project, Team, Worklog

def test_complete_user_workflow(client, auth):
    """Test complete user workflow from login to worklog creation"""
    # Login
    auth.login()
    
    # Create project
    project_data = {
        'name': 'Test Project',
        'description': 'Test Description'
    }
    response = client.post('/project/create', data=project_data)
    assert response.status_code == 302
    
    # Create team
    team_data = {
        'name': 'Test Team',
        'description': 'Test Team Description'
    }
    response = client.post('/team/create', data=team_data)
    assert response.status_code == 302
    
    # Add worklog
    worklog_data = {
        'project_id': 1,
        'description': 'Test worklog',
        'time_spent': 3600,
        'started': '2024-02-06T10:00:00'
    }
    response = client.post('/worklog/create', data=worklog_data)
    assert response.status_code == 302 