import pytest
from datetime import datetime, timedelta
from app.models.team import Team
from app.models.user import User
from app.models.worklog import Worklog
from app.extensions import db

@pytest.fixture
def setup_edge_case_data(app):
    """Fixture przygotowujący dane do testów przypadków brzegowych."""
    with app.app_context():
        # Tworzenie zespołu
        team = Team(name='Edge Case Team')
        db.session.add(team)
        
        # Użytkownik z bardzo dużą liczbą godzin
        overworked_user = User(
            username='overworked_user',
            email='overworked@test.com'
        )
        overworked_user.set_password('test123')
        db.session.add(overworked_user)
        
        # Użytkownik bez worklogów
        inactive_user = User(
            username='inactive_user',
            email='inactive@test.com'
        )
        inactive_user.set_password('test123')
        db.session.add(inactive_user)
        
        db.session.flush()
        
        # Dodawanie członków do zespołu
        team.add_user(overworked_user, 'member')
        team.add_user(inactive_user, 'member')
        
        # Dodaj worklog z bardzo dużą liczbą godzin
        worklog = Worklog(
            user_id=overworked_user.id,
            issue_key='EDGE-1',
            project_key='EDGE',
            work_date=datetime(2023, 1, 1).date(),
            time_spent=24.0
        )
        db.session.add(worklog)
        
        db.session.commit()
        return {'team': team}

def test_workload_with_overwork(app, setup_edge_case_data):
    """Test obciążenia z przekroczeniem normy godzin."""
    with app.app_context():
        team = setup_edge_case_data['team']
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 1, 1)
        
        workload = team.get_workload(start_date, end_date)
        user_workload = workload['users']['overworked_user']
        
        assert user_workload['hours'] == 24.0
        assert user_workload['percentage'] > 200  # Ponad 200% normy

def test_workload_with_inactive_user(app, setup_edge_case_data):
    """Test obciążenia dla nieaktywnego użytkownika."""
    with app.app_context():
        team = setup_edge_case_data['team']
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 1, 1)
        
        workload = team.get_workload(start_date, end_date)
        
        assert 'inactive_user' in workload['users']
        assert workload['users']['inactive_user']['hours'] == 0
        assert workload['users']['inactive_user']['percentage'] == 0

def test_stats_with_invalid_dates(app, setup_edge_case_data):
    """Test statystyk dla nieprawidłowych dat."""
    with app.app_context():
        team = setup_edge_case_data['team']
        
        # Data końcowa przed początkową
        start_date = datetime(2023, 1, 2)
        end_date = datetime(2023, 1, 1)
        
        with pytest.raises(ValueError):
            team.get_workload(start_date, end_date)

def test_stats_with_future_dates(app, setup_edge_case_data):
    """Test statystyk dla dat w przyszłości."""
    with app.app_context():
        team = setup_edge_case_data['team']
        
        start_date = datetime.now() + timedelta(days=1)
        end_date = datetime.now() + timedelta(days=7)
        
        stats = team.get_activity(start_date, end_date)
        assert stats['total_hours'] == 0
        assert stats['total_tasks'] == 0

def test_member_stats_nonexistent_user(app, setup_edge_case_data):
    """Test statystyk dla nieistniejącego użytkownika."""
    with app.app_context():
        team = setup_edge_case_data['team']
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 1, 1)
        
        with pytest.raises(ValueError):
            team.get_member_stats('nonexistent_user', start_date, end_date)

def test_project_stats_nonexistent_project(app, setup_edge_case_data):
    """Test statystyk dla nieistniejącego projektu."""
    with app.app_context():
        team = setup_edge_case_data['team']
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 1, 1)
        
        stats = team.get_project_stats('NONEXISTENT', start_date, end_date)
        assert stats['total_hours'] == 0
        assert stats['total_tasks'] == 0
        assert len(stats['users']) == 0

def test_export_with_special_characters(client, auth, setup_edge_case_data):
    """Test eksportu z użyciem znaków specjalnych."""
    auth.login()
    team = setup_edge_case_data['team']
    
    # Test eksportu CSV z polskimi znakami
    response = client.get(
        f'/api/teams/{team.id}/members/użytkownik/stats/export?format=csv'
    )
    assert response.status_code == 404  # Użytkownik nie istnieje

def test_long_period_stats(app, setup_edge_case_data):
    """Test statystyk dla bardzo długiego okresu."""
    with app.app_context():
        team = setup_edge_case_data['team']
        start_date = datetime(2020, 1, 1)
        end_date = datetime(2025, 12, 31)
        
        stats = team.get_activity(start_date, end_date)
        assert isinstance(stats['total_hours'], float)
        assert isinstance(stats['total_tasks'], int)

def test_concurrent_access(app, setup_edge_case_data):
    """Test równoczesnego dostępu do statystyk."""
    import threading
    
    def get_stats():
        with app.app_context():
            team = setup_edge_case_data['team']
            start_date = datetime(2023, 1, 1)
            end_date = datetime(2023, 1, 1)
            return team.get_workload(start_date, end_date)
    
    threads = []
    results = []
    
    # Uruchom 10 równoczesnych zapytań
    for _ in range(10):
        thread = threading.Thread(target=lambda: results.append(get_stats()))
        threads.append(thread)
        thread.start()
    
    # Poczekaj na zakończenie wszystkich wątków
    for thread in threads:
        thread.join()
    
    # Sprawdź czy wszystkie wyniki są spójne
    first_result = results[0]
    for result in results[1:]:
        assert result == first_result 