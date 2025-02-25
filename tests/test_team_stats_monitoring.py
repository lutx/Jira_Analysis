import pytest
from datetime import datetime
from app.monitoring import StatsMonitor
from app.models.team import Team

def test_stats_execution_time(app, test_team):
    """Test monitorowania czasu wykonania statystyk."""
    with app.app_context():
        monitor = StatsMonitor()
        
        with monitor.measure('workload_stats'):
            start_date = datetime(2023, 1, 1)
            end_date = datetime(2023, 1, 31)
            test_team.get_workload(start_date, end_date)
        
        metrics = monitor.get_metrics()
        assert 'workload_stats' in metrics
        assert metrics['workload_stats']['avg_time'] > 0
        assert metrics['workload_stats']['count'] == 1

def test_stats_error_monitoring(app, test_team):
    """Test monitorowania błędów w statystykach."""
    with app.app_context():
        monitor = StatsMonitor()
        
        try:
            with monitor.measure('invalid_stats'):
                raise ValueError("Test error")
        except ValueError:
            pass
        
        metrics = monitor.get_metrics()
        assert metrics['invalid_stats']['error_count'] == 1
        assert 'ValueError' in metrics['invalid_stats']['last_error']

def test_stats_memory_monitoring(app, test_team):
    """Test monitorowania zużycia pamięci."""
    with app.app_context():
        monitor = StatsMonitor()
        
        with monitor.measure_memory('workload_stats'):
            start_date = datetime(2023, 1, 1)
            end_date = datetime(2023, 1, 31)
            test_team.get_workload(start_date, end_date)
        
        metrics = monitor.get_metrics()
        assert metrics['workload_stats']['memory_used'] > 0
        assert metrics['workload_stats']['peak_memory'] > 0

def test_stats_query_monitoring(app, test_team):
    """Test monitorowania zapytań do bazy danych."""
    with app.app_context():
        monitor = StatsMonitor()
        
        with monitor.measure_queries('workload_stats'):
            start_date = datetime(2023, 1, 1)
            end_date = datetime(2023, 1, 31)
            test_team.get_workload(start_date, end_date)
        
        metrics = monitor.get_metrics()
        assert metrics['workload_stats']['query_count'] > 0
        assert len(metrics['workload_stats']['slow_queries']) >= 0

def test_monitoring_data_export(app, test_team):
    """Test eksportu danych monitorowania."""
    with app.app_context():
        monitor = StatsMonitor()
        
        # Wykonaj kilka operacji
        for _ in range(5):
            with monitor.measure('test_stats'):
                start_date = datetime(2023, 1, 1)
                end_date = datetime(2023, 1, 31)
                test_team.get_workload(start_date, end_date)
        
        # Eksportuj metryki
        export_data = monitor.export_metrics()
        
        assert 'timestamp' in export_data
        assert 'metrics' in export_data
        assert 'test_stats' in export_data['metrics']
        assert export_data['metrics']['test_stats']['count'] == 5 