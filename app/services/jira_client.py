from jira import JIRA
from typing import List, Dict, Any
from datetime import datetime
from flask import current_app
from app.models.jira_config import JiraConfig
import urllib3
import warnings
import logging

# Wyłącz ostrzeżenia o niezweryfikowanym HTTPS
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logger = logging.getLogger(__name__)

class JiraClient:
    def __init__(self) -> None:
        # Pobierz aktywną konfigurację JIRA
        config = JiraConfig.query.filter_by(is_active=True).first()
        if not config:
            raise ValueError("No active JIRA configuration found")
            
        # Initialize JIRA client
        self.jira: Any = JIRA(
            server=config.url,
            basic_auth=(config.username, config.api_token),
            options={
                'verify': current_app.config.get('VERIFY_SSL', False),
                'check_update': False,  # Wyłącz sprawdzanie aktualizacji
                'client_cert': None,    # Wyłącz certyfikat klienta
                'timeout': 30           # Ustaw timeout na 30 sekund
            }
        )
        
    def get_user_worklogs(self, username: str, since: datetime) -> List[Dict[str, Any]]:
        """
        Get worklogs for a specific user since given datetime
        """
        try:
            # Build JQL query for 2025 or since last sync
            if since.year < 2025:
                # Użyj poprawnego formatu daty YYYY/MM/DD
                jql = f'worklogAuthor = "{username}" AND worklogDate >= "2025/01/01"'
            else:
                # Formatuj datę w formacie YYYY/MM/DD
                since_str = since.strftime('%Y/%m/%d')
                jql = f'worklogAuthor = "{username}" AND worklogDate >= "{since_str}"'
            
            current_app.logger.debug(f"Processing user {username} with JQL: {jql}")
            
            # Get issues with worklogs
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                issues = self.jira.search_issues(
                    jql,
                    fields=['worklog', 'summary', 'project'],
                    maxResults=1000
                )
            
            current_app.logger.debug(f"Found {len(issues)} issues with worklogs for user {username}")
            
            worklogs = []
            for issue in issues:
                try:
                    # Get full worklog data
                    worklog_list = self.jira.worklogs(issue.key)
                    
                    for worklog in worklog_list:
                        # Check if worklog belongs to user (case insensitive)
                        author_email = getattr(worklog.author, 'emailAddress', '').lower()
                        author_name = getattr(worklog.author, 'name', '').lower()
                        user_email = username.lower()
                        
                        if author_email == user_email or author_name == user_email:
                            worklogs.append({
                                'id': worklog.id,
                                'issueKey': issue.key,
                                'summary': issue.fields.summary,
                                'project': issue.fields.project.key,
                                'timeSpentSeconds': worklog.timeSpentSeconds,
                                'started': worklog.started,
                                'created': worklog.created,
                                'updated': getattr(worklog, 'updated', None),
                                'author': {
                                    'name': worklog.author.name,
                                    'displayName': worklog.author.displayName,
                                    'emailAddress': getattr(worklog.author, 'emailAddress', None)
                                }
                            })
                except Exception as e:
                    current_app.logger.warning(f"Error processing issue {issue.key}: {str(e)}")
                    continue
            
            current_app.logger.debug(f"Found {len(worklogs)} worklogs for user {username}")
            return worklogs
            
        except Exception as e:
            current_app.logger.error(f"Error getting worklogs for user {username}: {str(e)}", exc_info=True)
            raise

def get_jira_client() -> JiraClient:
    return JiraClient() 