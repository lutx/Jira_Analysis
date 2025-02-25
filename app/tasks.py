# Obsługa długotrwałych operacji w tle
# Generowanie raportów asynchronicznie
# Okresowe czyszczenie cache'u 

from celery import Celery
from app.extensions import db
from app.models import Worklog, ProjectAssignment, UserAvailability
from datetime import datetime, timedelta
import pandas as pd
import logging

celery = Celery('tasks', broker='redis://localhost:6379/0')
logger = logging.getLogger(__name__)

@celery.task
def sync_jira_worklogs():
    """Synchronize worklogs from JIRA."""
    try:
        jira_service = get_jira_service()
        if not jira_service:
            logger.error("JIRA service not available")
            return False

        # Pobierz worklogi z ostatnich 24h
        yesterday = datetime.now() - timedelta(days=1)
        worklogs = jira_service.get_worklogs_since(yesterday)
        
        for worklog in worklogs:
            save_worklog(worklog)
            
        return True
    except Exception as e:
        logger.error(f"Error syncing worklogs: {str(e)}")
        return False

@celery.task
def calculate_portfolio_stats():
    """Calculate and cache portfolio statistics."""
    # Implementation...

@celery.task
def generate_monthly_reports():
    """Generate monthly PDF reports."""
    # Implementation...

@celery.task
def import_leave_data(file_path):
    """Import leave data from CSV."""
    try:
        df = pd.read_csv(file_path)
        for _, row in df.iterrows():
            UserAvailability.create(
                user_id=row['user_id'],
                date=row['date'],
                is_leave=True,
                note=row['note']
            )
        return True
    except Exception as e:
        logger.error(f"Error importing leave data: {str(e)}")
        return False 