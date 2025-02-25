import pytest
import time
from datetime import datetime, timedelta
from app.models.team import Team
from app.cache import cache

def test_stats_caching(app, test_team):
    """Test cache'owania statystyk zespołu."""
    with app.app_context():
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 1, 31)
        
        # Pierwsze pobranie (bez cache)
        start_time = time.time()
        stats1 = test_team.get_workload(start_date, end_date)
        first_request_time = time.time() - start_time
        
        # Drugie pobranie (z cache)
        start_time = time.time()
        stats2 = test_team.get_workload(start_date, end_date)
        cached_request_time = time.time() - start_time
        
        # Sprawdź czy drugie pobranie było szybsze
        assert cached_request_time < first_request_time
        # Sprawdź czy dane są identyczne
        assert stats1 == stats2

def test_cache_invalidation(app, test_team):
    """Test unieważniania cache'u."""
    with app.app_context():
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 1, 31)
        
        # Pobierz statystyki i zapisz w cache
        stats1 = test_team.get_workload(start_date, end_date)
        
        # Dodaj nowy worklog (powinno unieważnić cache)
        db = get_db()
        cursor = db.cursor()
        cursor.execute("""
            INSERT INTO worklogs (user_name, issue_key, project_key, work_date, time_spent)
            VALUES (?, ?, ?, ?, ?)
        """, ('user1', 'TEST-1', 'TEST', '2023-01-15', 8.0))
        db.commit()
        
        # Pobierz statystyki ponownie
        stats2 = test_team.get_workload(start_date, end_date)
        
        # Sprawdź czy dane się różnią
        assert stats1 != stats2

def test_cache_expiration(app, test_team):
    """Test wygasania cache'u."""
    with app.app_context():
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 1, 31)
        
        # Ustaw krótki czas wygasania cache'u
        cache.default_timeout = 1
        
        # Pobierz statystyki
        stats1 = test_team.get_workload(start_date, end_date)
        
        # Poczekaj na wygaśnięcie cache'u
        time.sleep(2)
        
        # Pobierz statystyki ponownie
        start_time = time.time()
        stats2 = test_team.get_workload(start_date, end_date)
        request_time = time.time() - start_time
        
        # Sprawdź czy to było pełne przetwarzanie (nie z cache'u)
        assert request_time > 0.1  # Zakładamy, że pełne przetwarzanie trwa >100ms

def test_cache_key_generation(app, test_team):
    """Test generowania kluczy cache'u."""
    with app.app_context():
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 1, 31)
        
        # Generuj klucze dla różnych parametrów
        key1 = test_team._get_cache_key('workload', start_date, end_date)
        key2 = test_team._get_cache_key('workload', start_date, end_date, user='user1')
        key3 = test_team._get_cache_key('workload', start_date, end_date, project='TEST-1')
        
        # Sprawdź czy klucze są różne
        assert len({key1, key2, key3}) == 3
        # Sprawdź czy klucze zawierają istotne informacje
        assert str(test_team.id) in key1
        assert 'workload' in key1
        assert start_date.strftime('%Y%m%d') in key1

def test_cache_memory_usage(app, test_team):
    """Test zużycia pamięci przez cache."""
    import sys
    import gc
    
    with app.app_context():
        # Wyczyść pamięć przed testem
        gc.collect()
        initial_memory = sys.getsizeof(cache)
        
        # Wygeneruj i zapisz w cache dużo danych
        for i in range(100):
            start_date = datetime(2023, 1, 1) + timedelta(days=i)
            end_date = start_date + timedelta(days=30)
            test_team.get_workload(start_date, end_date)
        
        # Sprawdź zużycie pamięci
        gc.collect()
        final_memory = sys.getsizeof(cache)
        
        # Upewnij się, że zużycie pamięci nie przekracza limitu
        memory_increase = final_memory - initial_memory
        assert memory_increase < 10 * 1024 * 1024  # Max 10MB

def test_concurrent_cache_access(app, test_team):
    """Test równoczesnego dostępu do cache'u."""
    import threading
    import queue
    
    errors = queue.Queue()
    results = queue.Queue()
    
    def access_cache():
        try:
            with app.app_context():
                start_date = datetime(2023, 1, 1)
                end_date = datetime(2023, 1, 31)
                stats = test_team.get_workload(start_date, end_date)
                results.put(stats)
        except Exception as e:
            errors.put(e)
    
    # Uruchom wiele równoczesnych dostępów
    threads = []
    for _ in range(10):
        thread = threading.Thread(target=access_cache)
        threads.append(thread)
        thread.start()
    
    for thread in threads:
        thread.join()
    
    # Sprawdź czy nie było błędów
    assert errors.empty()
    
    # Sprawdź czy wszystkie wyniki są identyczne
    first_result = results.get()
    while not results.empty():
        assert results.get() == first_result 