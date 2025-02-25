import pytest
from datetime import datetime, timedelta
from app.models.team import Team

def test_get_member_stats(client, auth, test_team, test_user):
    """Test pobierania statystyk członka zespołu."""
    auth.login()
    
    response = client.get(f'/api/teams/{test_team.id}/members/{test_user.user_name}/stats')
    assert response.status_code == 200
    
    data = response.get_json()
    assert 'total_hours' in data
    assert 'total_tasks' in data
    assert 'daily_stats' in data
    assert 'projects' in data
    assert 'trend' in data

def test_get_project_stats(client, auth, test_team):
    """Test pobierania statystyk projektu."""
    auth.login()
    
    response = client.get(f'/api/teams/{test_team.id}/projects/TEST-1/stats')
    assert response.status_code == 200
    
    data = response.get_json()
    assert 'total_hours' in data
    assert 'total_tasks' in data
    assert 'users' in data
    assert 'avg_hours_per_user' in data

def test_export_member_stats(client, auth, test_team, test_user):
    """Test eksportu statystyk członka zespołu."""
    auth.login()
    
    # Test eksportu CSV
    response = client.get(
        f'/api/teams/{test_team.id}/members/{test_user.user_name}/stats/export?format=csv'
    )
    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'text/csv'
    
    # Test eksportu PDF
    response = client.get(
        f'/api/teams/{test_team.id}/members/{test_user.user_name}/stats/export?format=pdf'
    )
    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'application/pdf'

def test_export_project_stats(client, auth, test_team):
    """Test eksportu statystyk projektu."""
    auth.login()
    
    # Test eksportu CSV
    response = client.get(
        f'/api/teams/{test_team.id}/projects/TEST-1/stats/export?format=csv'
    )
    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'text/csv'
    
    # Test eksportu PDF
    response = client.get(
        f'/api/teams/{test_team.id}/projects/TEST-1/stats/export?format=pdf'
    )
    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'application/pdf'

def test_invalid_team_id(client, auth):
    """Test obsługi nieprawidłowego ID zespołu."""
    auth.login()
    
    response = client.get('/api/teams/999/members/user1/stats')
    assert response.status_code == 404
    
    response = client.get('/api/teams/999/projects/TEST-1/stats')
    assert response.status_code == 404

def test_unauthorized_access(client):
    """Test dostępu bez autoryzacji."""
    response = client.get('/api/teams/1/members/user1/stats')
    assert response.status_code == 401
    
    response = client.get('/api/teams/1/projects/TEST-1/stats')
    assert response.status_code == 401

@pytest.fixture
def test_team(app):
    """Fixture tworzący testowy zespół."""
    with app.app_context():
        team = Team(name='Test Team', description='Test Description')
        team.save()
        return team 