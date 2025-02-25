from app.extensions import db
from app.models import User, Project, WorkLog
from jira import JIRA
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class JiraSync:
    def __init__(self, app=None):
        self.app = app
        self.jira_client = None
        if app:
            self.init_app(app)

    def init_app(self, app):
        """Initialize JIRA client with app configuration."""
        self.app = app
        try:
            self.jira_client = JIRA(
                server=app.config['JIRA_URL'],
                basic_auth=(
                    app.config['JIRA_USERNAME'],
                    app.config['JIRA_API_TOKEN']
                )
            )
        except Exception as e:
            logger.error(f"Failed to initialize JIRA client: {str(e)}")

    def sync_users(self):
        """Synchronize users from JIRA."""
        try:
            jira_users = self.jira_client.search_users(maxResults=False)
            for jira_user in jira_users:
                user = User.query.filter_by(jira_id=jira_user.accountId).first()
                if not user:
                    user = User(
                        username=jira_user.displayName,
                        email=jira_user.emailAddress,
                        jira_id=jira_user.accountId
                    )
                    db.session.add(user)
            db.session.commit()
            return True
        except Exception as e:
            logger.error(f"Error syncing users: {str(e)}")
            db.session.rollback()
            return False

    def sync_projects(self):
        """Synchronize projects from JIRA."""
        try:
            jira_projects = self.jira_client.projects()
            for jira_project in jira_projects:
                project = Project.query.filter_by(jira_id=jira_project.id).first()
                if not project:
                    project = Project(
                        name=jira_project.name,
                        key=jira_project.key,
                        jira_id=jira_project.id
                    )
                    db.session.add(project)
            db.session.commit()
            return True
        except Exception as e:
            logger.error(f"Error syncing projects: {str(e)}")
            db.session.rollback()
            return False

    def sync_worklogs(self, days_back=30):
        """Synchronize worklogs from JIRA."""
        try:
            since = datetime.now() - timedelta(days=days_back)
            jql = f'worklogDate >= "{since.strftime("%Y-%m-%d")}"'
            issues = self.jira_client.search_issues(jql, maxResults=False)
            
            for issue in issues:
                worklogs = self.jira_client.worklogs(issue.id)
                for worklog in worklogs:
                    existing_worklog = WorkLog.query.filter_by(
                        jira_id=worklog.id
                    ).first()
                    
                    if not existing_worklog:
                        new_worklog = WorkLog(
                            jira_id=worklog.id,
                            issue_key=issue.key,
                            time_spent=worklog.timeSpentSeconds,
                            comment=worklog.comment,
                            started=worklog.started,
                            author_id=worklog.author.accountId
                        )
                        db.session.add(new_worklog)
            
            db.session.commit()
            return True
        except Exception as e:
            logger.error(f"Error syncing worklogs: {str(e)}")
            db.session.rollback()
            return False 