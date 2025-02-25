import pytest
import time
from datetime import datetime, timedelta
from app.models.team import Team
from app.database import get_db

def test_workload_performance(app, setup_test_data_large):
    """Test wydajności obliczania obciążenia zespołu."""
    with app.app_context():
        team = setup_test_data_large['team']
        start_date = datetime.now() - timedelta(days=30)
        end_date = datetime.now()
        
        start_time = time.time()
        workload = team.get_workload(start_date, end_date)
        execution_time = time.time() - start_time
        
        assert execution_time < 1.0  # Powinno wykonać się w mniej niż 1 sekundę
        assert len(workload['users']) > 0

def test_export_performance(app, setup_test_data_large):
    """Test wydajności eksportu danych."""
    with app.app_context():
        team = setup_test_data_large['team']
        start_date = datetime.now() - timedelta(days=30)
        end_date = datetime.now()
        
        start_time = time.time()
        stats = team.get_member_stats('user1', start_date, end_date)
        export_time = time.time() - start_time
        
        assert export_time < 2.0  # Eksport powinien trwać mniej niż 2 sekundy

@pytest.fixture
def setup_test_data_large(app):
    """Fixture tworzący duży zestaw danych testowych."""
    with app.app_context():
        team = Team(name='Performance Test Team')
        team.save()
        
        # Dodaj 100 użytkowników i 1000 worklogów
        db = get_db()
        cursor = db.cursor()
        
        for i in range(100):
            user_name = f'perf_user_{i}'
            cursor.execute("""
                INSERT INTO users (user_name, display_name, email)
                VALUES (?, ?, ?)
            """, (user_name, f'User {i}', f'user{i}@test.com'))
            
            team.add_member(user_name, 'member')
            
            # Dodaj worklogi dla każdego użytkownika
            for j in range(10):
                date = datetime.now() - timedelta(days=j)
                cursor.execute("""
                    INSERT INTO worklogs (user_name, issue_key, project_key, work_date, time_spent)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    user_name,
                    f'PERF-{j}',
                    'PERF',
                    date.strftime('%Y-%m-%d'),
                    8.0
                ))
        
        db.commit()
        return {'team': team} 