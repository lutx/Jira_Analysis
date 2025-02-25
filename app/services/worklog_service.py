from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone
from app.models.worklog import Worklog
from app.services.jira_service import get_jira_service
from flask import current_app
import logging
from app.extensions import db

logger = logging.getLogger(__name__)

class WorklogService:
    MAX_HOURS_PER_DAY = 24
    MAX_HOURS_PER_ENTRY = 12
    
    @staticmethod
    def create_worklog(data: Dict[str, Any]) -> Worklog:
        """Creates a new worklog entry."""
        try:
            worklog = Worklog.from_dict(data)
            worklog.save()
            return worklog
        except Exception as e:
            logger.error(f"Error creating worklog: {str(e)}")
            raise

    @staticmethod
    def get_user_worklogs(user_name: str, 
                         start_date: Optional[datetime] = None,
                         end_date: Optional[datetime] = None) -> List[Worklog]:
        """Retrieves worklogs for a specific user."""
        try:
            return Worklog.get_by_user(user_name, start_date, end_date)
        except Exception as e:
            logger.error(f"Error getting user worklogs: {str(e)}")
            raise

    @staticmethod
    def sync_jira_worklogs(days: int = 30) -> Dict[str, int]:
        """Synchronizes worklogs from Jira."""
        try:
            jira = get_jira_service()
            start_date = datetime.now() - timedelta(days=days)
            
            stats = {
                'added': 0,
                'updated': 0,
                'errors': 0
            }

            # Get worklogs from Jira
            jira_worklogs = jira.get_worklogs(start_date=start_date)
            
            for jira_worklog in jira_worklogs:
                try:
                    worklog_data = {
                        'user_name': jira_worklog['author']['name'],
                        'project_key': jira_worklog['issue']['key'].split('-')[0],
                        'issue_key': jira_worklog['issue']['key'],
                        'time_spent': jira_worklog['timeSpentSeconds'] / 3600,  # Convert to hours
                        'work_date': datetime.fromisoformat(jira_worklog['started']).date(),
                        'description': jira_worklog.get('comment', '')
                    }

                    # Check if worklog already exists
                    existing_worklog = Worklog.get_by_id(jira_worklog['id'])
                    
                    if existing_worklog:
                        worklog_data['id'] = existing_worklog.id
                        Worklog.from_dict(worklog_data).save()
                        stats['updated'] += 1
                    else:
                        Worklog.from_dict(worklog_data).save()
                        stats['added'] += 1

                except Exception as e:
                    logger.error(f"Error processing worklog: {str(e)}")
                    stats['errors'] += 1

            return stats

        except Exception as e:
            logger.error(f"Error syncing Jira worklogs: {str(e)}")
            raise

    @staticmethod
    def get_worklog_summary(start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Generates a summary of worklogs for the given period."""
        try:
            db = get_db()
            cursor = db.cursor()

            cursor.execute("""
                SELECT 
                    user_name,
                    project_key,
                    SUM(time_spent) as total_hours,
                    COUNT(DISTINCT issue_key) as issues_count
                FROM worklogs
                WHERE work_date BETWEEN ? AND ?
                GROUP BY user_name, project_key
                ORDER BY user_name, total_hours DESC
            """, (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))

            summary = {}
            for row in cursor.fetchall():
                user = row['user_name']
                if user not in summary:
                    summary[user] = {
                        'total_hours': 0,
                        'projects': {},
                        'issues_count': 0
                    }
                
                summary[user]['total_hours'] += row['total_hours']
                summary[user]['issues_count'] += row['issues_count']
                summary[user]['projects'][row['project_key']] = {
                    'hours': row['total_hours'],
                    'issues': row['issues_count']
                }

            return summary

        except Exception as e:
            logger.error(f"Error generating worklog summary: {str(e)}")
            raise

    @staticmethod
    def validate_worklog(time_spent: int, started: datetime) -> tuple[bool, Optional[str]]:
        """Validate worklog entry."""
        # Check if date is not in future
        if started > datetime.now(timezone.utc):
            return False, "Cannot log time for future dates"
            
        # Check hours limit per entry
        hours = time_spent / 3600
        if hours > WorklogService.MAX_HOURS_PER_ENTRY:
            return False, f"Cannot log more than {WorklogService.MAX_HOURS_PER_ENTRY} hours per entry"
            
        # Check daily limit
        day_total = Worklog.query.filter(
            Worklog.started.date() == started.date()
        ).with_entities(db.func.sum(Worklog.time_spent)).scalar() or 0
        
        if (day_total + time_spent) / 3600 > WorklogService.MAX_HOURS_PER_DAY:
            return False, f"Total hours per day cannot exceed {WorklogService.MAX_HOURS_PER_DAY}"
            
        return True, None 