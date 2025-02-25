import pytest
from datetime import datetime
from io import BytesIO
from app.utils.export import (
    export_member_stats_csv,
    export_member_stats_pdf,
    export_project_stats_csv,
    export_project_stats_pdf
)

@pytest.fixture
def sample_member_stats():
    """Fixture z przykładowymi statystykami członka zespołu."""
    return {
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
        'projects': ['PROJ-1', 'PROJ-2']
    }

@pytest.fixture
def sample_project_stats():
    """Fixture z przykładowymi statystykami projektu."""
    return {
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

def test_export_member_stats_csv(app, test_team, sample_member_stats):
    """Test eksportu statystyk członka zespołu do CSV."""
    with app.app_context():
        response = export_member_stats_csv(
            test_team,
            'test_user',
            sample_member_stats,
            datetime(2023, 1, 1),
            datetime(2023, 1, 2)
        )
        
        assert response.status_code == 200
        assert response.headers['Content-Type'] == 'text/csv'
        assert 'member_stats_test_user_20230101.csv' in response.headers['Content-Disposition']
        
        # Sprawdź zawartość CSV
        csv_data = response.get_data(as_text=True)
        assert 'Data,Godziny,Zadania,Projekty' in csv_data
        assert '2023-01-01,8.0,3,"PROJ-1, PROJ-2"' in csv_data
        assert '2023-01-02,6.0,2,PROJ-1' in csv_data

def test_export_member_stats_pdf(app, test_team, sample_member_stats):
    """Test eksportu statystyk członka zespołu do PDF."""
    with app.app_context():
        response = export_member_stats_pdf(
            test_team,
            'test_user',
            sample_member_stats,
            datetime(2023, 1, 1),
            datetime(2023, 1, 2)
        )
        
        assert response.status_code == 200
        assert response.headers['Content-Type'] == 'application/pdf'
        assert 'member_stats_test_user_20230101.pdf' in response.headers['Content-Disposition']
        
        # Sprawdź czy dane są w formacie PDF
        pdf_data = response.get_data()
        assert pdf_data.startswith(b'%PDF')

def test_export_project_stats_csv(app, test_team, sample_project_stats):
    """Test eksportu statystyk projektu do CSV."""
    with app.app_context():
        response = export_project_stats_csv(
            test_team,
            'TEST-1',
            sample_project_stats,
            datetime(2023, 1, 1),
            datetime(2023, 1, 2)
        )
        
        assert response.status_code == 200
        assert response.headers['Content-Type'] == 'text/csv'
        assert 'project_stats_TEST-1_20230101.csv' in response.headers['Content-Disposition']
        
        # Sprawdź zawartość CSV
        csv_data = response.get_data(as_text=True)
        assert 'Użytkownik,Godziny,Zadania,Udział (%)' in csv_data
        assert 'user1,16.0,5,66.7' in csv_data
        assert 'user2,8.0,3,33.3' in csv_data

def test_export_project_stats_pdf(app, test_team, sample_project_stats):
    """Test eksportu statystyk projektu do PDF."""
    with app.app_context():
        response = export_project_stats_pdf(
            test_team,
            'TEST-1',
            sample_project_stats,
            datetime(2023, 1, 1),
            datetime(2023, 1, 2)
        )
        
        assert response.status_code == 200
        assert response.headers['Content-Type'] == 'application/pdf'
        assert 'project_stats_TEST-1_20230101.pdf' in response.headers['Content-Disposition']
        
        # Sprawdź czy dane są w formacie PDF
        pdf_data = response.get_data()
        assert pdf_data.startswith(b'%PDF')

def test_export_with_invalid_dates(app, test_team, sample_member_stats):
    """Test eksportu z nieprawidłowymi datami."""
    with app.app_context():
        with pytest.raises(ValueError):
            export_member_stats_csv(
                test_team,
                'test_user',
                sample_member_stats,
                datetime(2023, 1, 2),  # end_date przed start_date
                datetime(2023, 1, 1)
            )

def test_export_with_empty_stats(app, test_team):
    """Test eksportu pustych statystyk."""
    empty_stats = {
        'daily_stats': {},
        'total_hours': 0,
        'total_tasks': 0,
        'avg_daily_hours': 0,
        'avg_tasks_per_day': 0,
        'projects': []
    }
    
    with app.app_context():
        response = export_member_stats_csv(
            test_team,
            'test_user',
            empty_stats,
            datetime(2023, 1, 1),
            datetime(2023, 1, 2)
        )
        
        assert response.status_code == 200
        csv_data = response.get_data(as_text=True)
        assert 'Data,Godziny,Zadania,Projekty' in csv_data
        assert len(csv_data.splitlines()) == 1  # Tylko nagłówek 