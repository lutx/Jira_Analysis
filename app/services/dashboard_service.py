from datetime import datetime, timedelta
from typing import Dict, Any
import logging
from app.services.jira_service import get_jira_service

logger = logging.getLogger(__name__)

def get_dashboard_stats(username: str) -> Dict[str, Any]:
    """Pobiera statystyki dla dashboardu."""
    try:
        jira = get_jira_service()
        if not jira:
            logger.error("Jira service not initialized")
            raise ValueError("Jira service not initialized")
            
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        try:
            tasks = jira.search_issues(f'assignee = {username} AND status != Done')
            projects = jira.get_projects()
            worklog = jira.get_user_worklog(username, start_date, end_date)
        except Exception as e:
            logger.error(f"Error fetching Jira data: {str(e)}")
            raise
        
        return {
            'stats': {
                'tasks_count': len(tasks),
                'projects_count': len(projects),
                'reports_count': 0,
                'worklog_hours': worklog
            },
            'activity_data': [],
            'activity_labels': [],
            'status_data': [],
            'status_labels': [],
            'activities': []
        }
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {str(e)}")
        raise 