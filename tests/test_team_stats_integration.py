import pytest
from datetime import datetime
from app.models.team import Team
from app.models.user import User
from app.extensions import db

@pytest.fixture
def setup_test_data(app):
    """Fixture przygotowujący dane testowe."""
    with app.app_context():
        # Tworzenie użytkowników testowych
        users = [
            User(username='user1', email='user1@test.com'),
            User(username='user2', email='user2@test.com')
        ]
        for user in users:
            user.set_password('test123')
            db.session.add(user)
        
        db.session.flush()
        
        # Tworzenie zespołu
        team = Team(name='Test Team', description='Test Description')
        db.session.add(team)
        db.session.flush()
        
        # Dodawanie członków do zespołu
        team.add_user(users[0], 'member')
        team.add_user(users[1], 'member')
        
        db.session.commit()
        
        return {
            'team': team,
            'users': users,
            'start_date': datetime(2023, 1, 1),
            'end_date': datetime(2023, 1, 2)
        }

def test_team_workload_integration(app, setup_test_data):
    """Test integracyjny obciążenia zespołu."""
    with app.app_context():
        team = setup_test_data['team']
        start_date = setup_test_data['start_date']
        end_date = setup_test_data['end_date']
        
        workload = team.get_workload(start_date, end_date)
        
        assert workload['expected_hours'] > 0
        assert len(workload['users']) == 2
        assert workload['users']['user1']['hours'] == 14.0
        assert workload['users']['user2']['hours'] == 11.0

def test_team_activity_integration(app, setup_test_data):
    """Test integracyjny aktywności zespołu."""
    with app.app_context():
        team = setup_test_data['team']
        start_date = setup_test_data['start_date']
        end_date = setup_test_data['end_date']
        
        activity = team.get_activity(start_date, end_date)
        
        assert activity['total_hours'] == 25.0
        assert activity['total_tasks'] == 4
        assert len(activity['daily_activity']) == 2
        assert activity['daily_activity']['2023-01-01'] == 12.0
        assert activity['daily_activity']['2023-01-02'] == 13.0

def test_member_stats_integration(app, setup_test_data):
    """Test integracyjny statystyk członka zespołu."""
    with app.app_context():
        team = setup_test_data['team']
        start_date = setup_test_data['start_date']
        end_date = setup_test_data['end_date']
        
        stats = team.get_member_stats('user1', start_date, end_date)
        
        assert stats['total_hours'] == 14.0
        assert stats['total_tasks'] == 2
        assert len(stats['daily_stats']) == 2
        assert 'TEST' in stats['projects']
        assert stats['avg_daily_hours'] == 7.0

def test_project_stats_integration(app, setup_test_data):
    """Test integracyjny statystyk projektu."""
    with app.app_context():
        team = setup_test_data['team']
        start_date = setup_test_data['start_date']
        end_date = setup_test_data['end_date']
        
        stats = team.get_project_stats('TEST', start_date, end_date)
        
        assert stats['total_hours'] == 25.0
        assert stats['total_tasks'] == 4
        assert len(stats['users']) == 2
        assert stats['avg_hours_per_user'] == 12.5

def test_export_integration(client, auth, setup_test_data):
    """Test integracyjny eksportu statystyk."""
    auth.login()
    team = setup_test_data['team']
    
    # Test eksportu CSV
    response = client.get(f'/api/teams/{team.id}/members/user1/stats/export?format=csv')
    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'text/csv'
    
    # Test eksportu PDF
    response = client.get(f'/api/teams/{team.id}/projects/TEST/stats/export?format=pdf')
    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'application/pdf'

def test_api_endpoints_integration(client, auth, setup_test_data):
    """Test integracyjny endpointów API."""
    auth.login()
    team = setup_test_data['team']
    
    # Test pobierania statystyk członka zespołu
    response = client.get(f'/api/teams/{team.id}/members/user1/stats')
    assert response.status_code == 200
    data = response.get_json()
    assert data['total_hours'] == 14.0
    
    # Test pobierania statystyk projektu
    response = client.get(f'/api/teams/{team.id}/projects/TEST/stats')
    assert response.status_code == 200
    data = response.get_json()
    assert data['total_hours'] == 25.0

def test_views_integration(client, auth, setup_test_data):
    """Test integracyjny widoków."""
    auth.login()
    team = setup_test_data['team']
    
    # Test widoku statystyk członka zespołu
    response = client.get(f'/teams/{team.id}/members/user1/stats')
    assert response.status_code == 200
    assert b'Statystyki Członka Zespołu' in response.data
    
    # Test widoku statystyk projektu
    response = client.get(f'/teams/{team.id}/projects/TEST/stats')
    assert response.status_code == 200
    assert b'Statystyki Projektu' in response.data 