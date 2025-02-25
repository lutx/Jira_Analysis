import pytest
from datetime import datetime, timedelta
from app.models.team import Team
from app.exceptions import ValidationError

def test_validate_date_range():
    """Test walidacji zakresu dat."""
    team = Team(name='Test Team')
    
    # Prawidłowy zakres dat
    start_date = datetime(2023, 1, 1)
    end_date = datetime(2023, 1, 31)
    assert team._validate_date_range(start_date, end_date) is None
    
    # Data końcowa przed początkową
    with pytest.raises(ValidationError) as exc:
        team._validate_date_range(end_date, start_date)
    assert "Data końcowa nie może być wcześniejsza niż początkowa" in str(exc.value)
    
    # Zbyt długi okres
    start_date = datetime(2020, 1, 1)
    end_date = datetime(2025, 12, 31)
    with pytest.raises(ValidationError) as exc:
        team._validate_date_range(start_date, end_date)
    assert "Maksymalny okres to 2 lata" in str(exc.value)

def test_validate_user_access(app, test_team, test_user):
    """Test walidacji dostępu użytkownika."""
    with app.app_context():
        # Użytkownik jest członkiem zespołu
        assert test_team._validate_user_access(test_user.user_name) is None
        
        # Użytkownik nie jest członkiem zespołu
        with pytest.raises(ValidationError) as exc:
            test_team._validate_user_access('nonexistent_user')
        assert "Użytkownik nie jest członkiem zespołu" in str(exc.value)
        
        # Użytkownik jest nieaktywny
        test_team.deactivate_member(test_user.user_name)
        with pytest.raises(ValidationError) as exc:
            test_team._validate_user_access(test_user.user_name)
        assert "Użytkownik jest nieaktywny" in str(exc.value)

def test_validate_project_access(app, test_team):
    """Test walidacji dostępu do projektu."""
    with app.app_context():
        # Dodaj przykładowy projekt
        db = get_db()
        cursor = db.cursor()
        cursor.execute("""
            INSERT INTO team_projects (team_id, project_key)
            VALUES (?, ?)
        """, (test_team.id, 'TEST-1'))
        db.commit()
        
        # Projekt istnieje
        assert test_team._validate_project_access('TEST-1') is None
        
        # Projekt nie istnieje
        with pytest.raises(ValidationError) as exc:
            test_team._validate_project_access('NONEXISTENT')
        assert "Projekt nie jest przypisany do zespołu" in str(exc.value)

def test_validate_worklog_data():
    """Test walidacji danych worklogów."""
    team = Team(name='Test Team')
    
    # Prawidłowe dane
    worklog = {
        'time_spent': 8.0,
        'work_date': '2023-01-01',
        'issue_key': 'TEST-1'
    }
    assert team._validate_worklog_data(worklog) is None
    
    # Nieprawidłowa liczba godzin
    invalid_worklog = worklog.copy()
    invalid_worklog['time_spent'] = -1
    with pytest.raises(ValidationError) as exc:
        team._validate_worklog_data(invalid_worklog)
    assert "Liczba godzin musi być większa od 0" in str(exc.value)
    
    # Nieprawidłowy format daty
    invalid_worklog = worklog.copy()
    invalid_worklog['work_date'] = 'invalid_date'
    with pytest.raises(ValidationError) as exc:
        team._validate_worklog_data(invalid_worklog)
    assert "Nieprawidłowy format daty" in str(exc.value)

def test_validate_stats_filters():
    """Test walidacji filtrów statystyk."""
    team = Team(name='Test Team')
    
    # Prawidłowe filtry
    filters = {
        'start_date': '2023-01-01',
        'end_date': '2023-01-31',
        'group_by': 'day'
    }
    assert team._validate_stats_filters(filters) is None
    
    # Nieprawidłowy format grupowania
    invalid_filters = filters.copy()
    invalid_filters['group_by'] = 'invalid'
    with pytest.raises(ValidationError) as exc:
        team._validate_stats_filters(invalid_filters)
    assert "Nieprawidłowy format grupowania" in str(exc.value)
    
    # Brakujące wymagane pola
    invalid_filters = {'start_date': '2023-01-01'}
    with pytest.raises(ValidationError) as exc:
        team._validate_stats_filters(invalid_filters)
    assert "Brak wymaganego pola: end_date" in str(exc.value)

def test_validate_export_options():
    """Test walidacji opcji eksportu."""
    team = Team(name='Test Team')
    
    # Prawidłowe opcje
    options = {
        'format': 'csv',
        'include_details': True
    }
    assert team._validate_export_options(options) is None
    
    # Nieprawidłowy format
    invalid_options = options.copy()
    invalid_options['format'] = 'invalid'
    with pytest.raises(ValidationError) as exc:
        team._validate_export_options(invalid_options)
    assert "Nieobsługiwany format eksportu" in str(exc.value)

def test_validate_concurrent_access(app, test_team):
    """Test walidacji równoczesnego dostępu."""
    import threading
    import queue
    
    errors = queue.Queue()
    
    def validate_access():
        try:
            with app.app_context():
                test_team._validate_concurrent_access()
        except Exception as e:
            errors.put(e)
    
    # Uruchom wiele równoczesnych walidacji
    threads = []
    for _ in range(10):
        thread = threading.Thread(target=validate_access)
        threads.append(thread)
        thread.start()
    
    for thread in threads:
        thread.join()
    
    # Sprawdź czy nie było błędów
    assert errors.empty() 