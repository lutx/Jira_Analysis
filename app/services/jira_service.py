from typing import Dict, List, Optional, Any, Tuple
import requests
from flask import current_app
import logging
from datetime import datetime, timedelta
from flask_caching import Cache
from jira import JIRA, JIRAError
from functools import lru_cache, wraps
from app.models.jira_config import JiraConfig
from app.utils.crypto import decrypt_password
from app.extensions import db
import base64
from app.models.user import User
from app.models import Setting
import os
from app.models.role import Role
from contextlib import contextmanager
import urllib3
from app.models.project import Project
from app.models.worklog import Worklog
from app.models.issue import Issue
import tenacity
from app.exceptions import JiraConnectionError

logger = logging.getLogger(__name__)
cache = Cache()

class JiraService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(JiraService, cls).__new__(cls)
            cls._instance.initialize()
        return cls._instance

    def initialize(self) -> None:
        """Initialize service attributes."""
        self.jira = None
        self.config = None
        self._base_url = None
        self.initialize_from_config()

    def initialize_from_config(self) -> None:
        """Initialize JIRA client from active configuration."""
        try:
            self.config = JiraConfig.get_active_config()
            if self.config:
                self._base_url = self.config.url.rstrip('/')
                self.jira = self.config.get_jira_client()
                logger.info("JIRA service initialized successfully")
            else:
                logger.warning("No active JIRA configuration found")
        except Exception as e:
            logger.error(f"Failed to initialize JIRA service: {str(e)}")
            self.jira = None
            self.config = None
            self._base_url = None

    @property
    def is_configured(self) -> bool:
        """Check if JIRA is configured."""
        return bool(self.config and self._base_url)

    @property
    def is_connected(self) -> bool:
        """Check if JIRA connection is active."""
        if not self.is_configured:
            return False
        try:
            self.jira.server_info()
            return True
        except Exception as e:
            logger.error(f"JIRA connection check failed: {str(e)}")
            return False

    def ensure_connected(self):
        """Ensure JIRA connection is available."""
        if not self.is_configured:
            raise JiraConnectionError("JIRA is not configured")
        if not self.is_connected:
            raise JiraConnectionError("JIRA connection failed")

    def get_headers(self):
        """Get headers for JIRA API requests."""
        if not self.config:
            raise JiraConnectionError("No active JIRA configuration")
        return {
            'Authorization': self.config.get_basic_auth_header(),
            'Content-Type': 'application/json'
        }

    def make_request(self, endpoint: str, method: str = 'GET', **kwargs) -> requests.Response:
        """Make a request to JIRA API with proper error handling."""
        if not self._base_url:
            raise JiraConnectionError("JIRA base URL not configured")

        url = f"{self._base_url}{endpoint}"
        headers = self.get_headers()
        
        try:
            response = requests.request(method, url, headers=headers, verify=True, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"JIRA API request failed: {str(e)}")
            raise JiraConnectionError(f"JIRA API request failed: {str(e)}")

    @tenacity.retry(
        stop=tenacity.stop_after_attempt(3),
        wait=tenacity.wait_exponential(multiplier=1, min=4, max=10),
        retry=tenacity.retry_if_exception_type(JIRAError),
        before=tenacity.before_log(logger, logging.INFO),
        after=tenacity.after_log(logger, logging.INFO)
    )
    def sync_projects(self) -> Dict[str, Any]:
        """Synchronize projects from JIRA."""
        self.ensure_connected()
        logger.info("Starting project synchronization")
        
        stats = {
            'total': 0,
            'created': 0,
            'updated': 0,
            'errors': 0,
            'error_messages': []
        }

        try:
            # Get all projects from JIRA
            jira_projects = self.jira.projects()
            stats['total'] = len(jira_projects)
            
            for jira_project in jira_projects:
                try:
                    # Get detailed project info
                    project_details = self.jira.project(jira_project.key)
                    
                    # Map JIRA project data to our model
                    project_data = {
                        'name': jira_project.name,
                        'jira_key': jira_project.key,
                        'project_type': getattr(project_details, 'projectTypeKey', 'software'),
                        'description': getattr(project_details, 'description', '') or '',
                        'is_active': True,  # Default to active
                        'last_sync': datetime.utcnow()
                    }

                    # Try to find existing project
                    project = Project.query.filter_by(jira_key=jira_project.key).first()
                    
                    if project:
                        # Update existing project
                        for key, value in project_data.items():
                            setattr(project, key, value)
                        stats['updated'] += 1
                    else:
                        # Create new project
                        project = Project(**project_data)
                        db.session.add(project)
                        stats['created'] += 1

                    db.session.flush()  # Flush changes for this project

                except Exception as e:
                    error_msg = f"Error processing project {getattr(jira_project, 'key', 'unknown')}: {str(e)}"
                    logger.error(error_msg)
                    stats['errors'] += 1
                    stats['error_messages'].append(error_msg)

            # Commit all changes
            try:
                db.session.commit()
                logger.info(f"Project synchronization completed: {stats}")
            except Exception as e:
                db.session.rollback()
                error_msg = f"Failed to commit project changes: {str(e)}"
                logger.error(error_msg)
                stats['errors'] += 1
                stats['error_messages'].append(error_msg)
                raise

        except Exception as e:
            error_msg = f"Project synchronization failed: {str(e)}"
            logger.error(error_msg)
            stats['errors'] += 1
            stats['error_messages'].append(error_msg)
            raise JiraConnectionError(error_msg)

        return stats

    @tenacity.retry(
        stop=tenacity.stop_after_attempt(3),
        wait=tenacity.wait_exponential(multiplier=1, min=4, max=10),
        retry=tenacity.retry_if_exception_type(JIRAError),
        before=tenacity.before_log(logger, logging.INFO),
        after=tenacity.after_log(logger, logging.INFO)
    )
    def sync_users(self) -> Dict[str, Any]:
        """Synchronize users from JIRA."""
        self.ensure_connected()
        logger.info("Starting user synchronization")
        logger.info("=" * 50)
        logger.info("JIRA User Synchronization Debug Log")
        logger.info("=" * 50)
        
        stats = {
            'total': 0,
            'created': 0,
            'updated': 0,
            'errors': 0,
            'error_messages': [],
            'processed_users': []
        }

        try:
            from app.models.user import User
            from app.models.role import Role
            
            # Get default role
            default_role = Role.query.filter_by(name='user').first()
            if not default_role:
                error_msg = "Default role 'user' not found"
                logger.error(error_msg)
                raise ValueError(error_msg)

            logger.info(f"Found default role: {default_role.name}")
            start_at = 0
            max_results = 50
            total_processed = 0
            previous_batch_size = max_results
            max_iterations = 20  # Maksymalna liczba iteracji
            iteration_count = 0
            last_processed_user = None

            while True:
                iteration_count += 1
                logger.info(f"Iteration {iteration_count} of maximum {max_iterations}")
                
                if iteration_count > max_iterations:
                    logger.warning(f"Reached maximum number of iterations ({max_iterations}). Breaking loop.")
                    break

                try:
                    # Make request to JIRA API
                    endpoint = "/rest/api/2/user/search"
                    params = {
                        'username': '.',  # Match all users
                        'startAt': start_at,
                        'maxResults': max_results
                    }
                    
                    logger.info("-" * 30)
                    logger.info(f"Fetching batch of users from JIRA (startAt={start_at}, maxResults={max_results})")
                    response = self.make_request(endpoint, params=params)
                    users_data = response.json()
                    
                    current_batch_size = len(users_data)
                    logger.info(f"Retrieved {current_batch_size} users from JIRA")
                    logger.info(f"Response status code: {response.status_code}")

                    # Warunki wyjścia z pętli
                    if not users_data:
                        logger.info("No more users to process - empty response")
                        break

                    if current_batch_size == 0:
                        logger.info("Received empty batch - breaking loop")
                        break

                    if current_batch_size < max_results:
                        logger.info("Received less users than requested - last batch")
                        
                    # Sprawdź czy nie przetwarzamy tych samych użytkowników
                    first_user_in_batch = users_data[0].get('accountId') if users_data else None
                    if first_user_in_batch == last_processed_user:
                        logger.warning("Detected same user as in previous batch - breaking loop")
                        break

                    last_processed_user = first_user_in_batch

                    # Process each user in the batch
                    for jira_user in users_data:
                        try:
                            logger.info("-" * 20)
                            display_name = jira_user.get('displayName', 'Unknown')
                            logger.info(f"Processing user: {display_name}")

                            # Extract user data safely
                            user_data = {
                                'username': jira_user.get('name') or jira_user.get('emailAddress', '').split('@')[0],
                                'email': jira_user.get('emailAddress', ''),
                                'display_name': display_name,
                                'jira_key': jira_user.get('key') or None,
                                'jira_display_name': display_name,
                                'jira_email': jira_user.get('emailAddress', ''),
                                'jira_active': True if jira_user.get('active') is None else jira_user.get('active'),
                                'jira_id': jira_user.get('accountId') or None,
                                'jira_username': jira_user.get('name', ''),
                                'is_active': True if jira_user.get('active') is None else jira_user.get('active'),
                                'last_jira_sync': db.func.now()
                            }

                            # Validate required fields
                            if not any([user_data['username'], user_data['email'], user_data['display_name']]):
                                logger.warning(f"WARNING: Skipping user with no identifiers: {jira_user}")
                                continue

                            # Find existing user using multiple criteria
                            user = None
                            
                            # Try finding by jira_id if available
                            if user_data['jira_id']:
                                user = User.query.filter_by(jira_id=user_data['jira_id']).first()
                                if user:
                                    logger.info(f"Found existing user by jira_id: {user.username}")
                            
                            # Try finding by email
                            if not user and user_data['email']:
                                user = User.query.filter_by(email=user_data['email']).first()
                                if user:
                                    logger.info(f"Found existing user by email: {user.username}")

                            # Try finding by username
                            if not user and user_data['username']:
                                user = User.query.filter_by(username=user_data['username']).first()
                                if user:
                                    logger.info(f"Found existing user by username: {user.username}")

                            try:
                                if user:
                                    logger.info(f"Updating existing user: {user.username}")
                                    # Update existing user with non-None values
                                    for key, value in user_data.items():
                                        if value is not None:
                                            current_value = getattr(user, key)
                                            if current_value != value:
                                                logger.info(f"  Updating {key}: {current_value} -> {value}")
                                                setattr(user, key, value)
                                        
                                    # Ensure user has default role
                                    if default_role not in user.roles:
                                        logger.info(f"Adding default role to user: {user.username}")
                                        user.roles.append(default_role)
                                        
                                    stats['updated'] += 1
                                else:
                                    identifier = user_data['username'] or user_data['email'] or user_data['display_name']
                                    logger.info(f"Creating new user: {identifier}")
                                    # Create new user
                                    user = User(**user_data)
                                    if default_role not in user.roles:
                                        user.roles.append(default_role)
                                    db.session.add(user)
                                    stats['created'] += 1

                                # Track processed user
                                stats['processed_users'].append({
                                    'username': user_data['username'],
                                    'email': user_data['email'],
                                    'jira_id': user_data['jira_id'],
                                    'action': 'updated' if user else 'created'
                                })

                                total_processed += 1
                                
                                # Commit after each user
                                db.session.commit()
                                logger.info(f"Successfully saved user: {identifier}")

                            except Exception as e:
                                db.session.rollback()
                                error_msg = f"Database error processing user {display_name}: {str(e)}"
                                logger.error(error_msg)
                                stats['errors'] += 1
                                stats['error_messages'].append(error_msg)
                                continue

                        except Exception as e:
                            error_msg = f"Error processing user {display_name}: {str(e)}"
                            logger.error(error_msg)
                            stats['errors'] += 1
                            stats['error_messages'].append(error_msg)
                            continue

                    # Aktualizuj start_at tylko jeśli otrzymaliśmy pełną partię
                    if current_batch_size >= max_results:
                        start_at += current_batch_size
                        logger.info(f"Moving to next batch, startAt: {start_at}")
                    else:
                        logger.info("Last batch processed - breaking loop")
                        break

                    previous_batch_size = current_batch_size

                except Exception as e:
                    error_msg = f"Error fetching users from JIRA: {str(e)}"
                    logger.error(error_msg)
                    stats['errors'] += 1
                    stats['error_messages'].append(error_msg)
                    break

            stats['total'] = total_processed
            logger.info("=" * 50)
            logger.info("Synchronization Summary:")
            logger.info(f"Total iterations: {iteration_count}")
            logger.info(f"Total processed: {stats['total']}")
            logger.info(f"Created: {stats['created']}")
            logger.info(f"Updated: {stats['updated']}")
            logger.info(f"Errors: {stats['errors']}")
            if stats['error_messages']:
                logger.info("Error messages:")
                for msg in stats['error_messages']:
                    logger.info(f"  - {msg}")
            
            # Log final database state
            final_user_count = User.query.count()
            logger.info(f"Final user count in database: {final_user_count}")
            logger.info("=" * 50)
            
            return stats

        except Exception as e:
            error_msg = f"User synchronization failed: {str(e)}"
            logger.error(error_msg)
            stats['errors'] += 1
            stats['error_messages'].append(error_msg)
            raise JiraConnectionError(error_msg)

    @tenacity.retry(
        stop=tenacity.stop_after_attempt(3),
        wait=tenacity.wait_exponential(multiplier=1, min=4, max=10),
        retry=tenacity.retry_if_exception_type(JIRAError),
        before=tenacity.before_log(logger, logging.INFO),
        after=tenacity.after_log(logger, logging.INFO)
    )
    def sync_worklogs(self, days_back: int = 30) -> Dict[str, Any]:
        """Synchronize worklogs from JIRA."""
        try:
            # Initialize stats
            stats = {
                'total': 0,
                'created': 0,
                'updated': 0,
                'errors': 0,
                'error_messages': []
            }

            # Set date range for 2025
            start_date = datetime(2025, 1, 1)
            end_date = datetime(2025, 12, 31)
            logger.info(f"Starting worklog synchronization for 2025")

            # Get active projects from database
            projects = Project.query.filter_by(is_active=True).all()

            for project in projects:
                try:
                    logger.info(f"Fetching 2025 worklogs for project {project.jira_key}")
                    
                    # Check if project still exists in JIRA
                    try:
                        jira_project = self.jira.project(project.jira_key)
                    except JIRAError as je:
                        if je.status_code == 404 or 'does not exist' in str(je).lower():
                            # Project no longer exists in JIRA
                            logger.warning(f"Project {project.jira_key} no longer exists in JIRA, marking as inactive")
                            project.is_active = False
                            db.session.add(project)
                            db.session.commit()
                            continue
                        raise je

                    # Build JQL query for worklogs
                    jql = f'project = "{project.jira_key}" AND worklogDate >= "{start_date.strftime("%Y-%m-%d")}" AND worklogDate <= "{end_date.strftime("%Y-%m-%d")}"'
                    
                    try:
                        # Search for issues with worklogs
                        issues = self.jira.search_issues(
                            jql,
                            startAt=0,
                            fields=['worklog', 'summary'],
                            maxResults=1000
                        )
                    except JIRAError as je:
                        if je.status_code == 400 and 'does not exist for the field' in str(je):
                            # Project not found in JIRA search
                            logger.warning(f"Project {project.jira_key} not found in JIRA search, marking as inactive")
                            project.is_active = False
                            db.session.add(project)
                            db.session.commit()
                            continue
                        raise je

                    for issue in issues:
                        try:
                            # Get detailed worklog info
                            worklog = self.jira.worklogs(issue.id)
                            
                            for work_item in worklog:
                                try:
                                    # Skip if worklog is outside our date range
                                    started = datetime.strptime(work_item.started[:10], '%Y-%m-%d')
                                    if started < start_date or started > end_date:
                                        continue

                                    # Get user info safely
                                    author = work_item.author
                                    author_name = getattr(author, 'name', None)
                                    author_display_name = getattr(author, 'displayName', None)
                                    author_email = getattr(author, 'emailAddress', None)
                                    
                                    # Try to find user by various fields
                                    user = None
                                    if author_email:
                                        user = User.query.filter_by(email=author_email).first()
                                    if not user and author_name:
                                        user = User.query.filter_by(username=author_name).first()
                                    if not user and author_display_name:
                                        user = User.query.filter_by(display_name=author_display_name).first()
                                        
                                    if not user:
                                        # Create new user if not found
                                        user = User(
                                            username=author_name or author_email.split('@')[0] if author_email else 'unknown',
                                            email=author_email or f"{author_name}@unknown.com" if author_name else 'unknown@unknown.com',
                                            display_name=author_display_name or author_name or 'Unknown User',
                                            is_active=True
                                        )
                                        db.session.add(user)
                                        db.session.flush()  # Get the ID
                                        logger.info(f"Created new user: {user.username}")

                                    # Find or create issue
                                    issue_obj = Issue.query.filter_by(
                                        jira_key=issue.key
                                    ).first()
                                    
                                    if not issue_obj:
                                        # Create new issue
                                        issue_obj = Issue(
                                            jira_key=issue.key,
                                            summary=issue.fields.summary,
                                            project_id=project.id
                                        )
                                        db.session.add(issue_obj)
                                        db.session.flush()  # Get the ID

                                    # Extract worklog data
                                    worklog_data = {
                                        'jira_worklog_id': str(work_item.id),
                                        'issue_id': issue_obj.id,
                                        'user_id': user.id,
                                        'project_id': project.id,
                                        'time_spent': work_item.timeSpentSeconds / 3600,  # Convert to hours
                                        'time_spent_seconds': work_item.timeSpentSeconds,
                                        'work_date': started.date(),
                                        'description': getattr(work_item, 'comment', '') or '',
                                        'updated_at': datetime.utcnow()
                                    }

                                    # Find existing worklog
                                    existing_worklog = Worklog.query.filter_by(
                                        jira_worklog_id=str(work_item.id)  # Use correct field name
                                    ).first()

                                    if existing_worklog:
                                        # Update existing worklog
                                        for key, value in worklog_data.items():
                                            setattr(existing_worklog, key, value)
                                        stats['updated'] += 1
                                    else:
                                        # Create new worklog
                                        new_worklog = Worklog(**worklog_data)
                                        db.session.add(new_worklog)
                                        stats['created'] += 1

                                    db.session.flush()
                                    stats['total'] += 1

                                except Exception as e:
                                    error_msg = f"Error processing worklog {work_item.id} for issue {issue.key}: {str(e)}"
                                    logger.error(error_msg)
                                    stats['errors'] += 1
                                    stats['error_messages'].append(error_msg)
                                    db.session.rollback()

                        except Exception as e:
                            error_msg = f"Error fetching worklogs for issue {issue.key}: {str(e)}"
                            logger.error(error_msg)
                            stats['errors'] += 1
                            stats['error_messages'].append(error_msg)
                            continue

                except Exception as e:
                    error_msg = f"Error processing project {project.jira_key}: {str(e)}"
                    logger.error(error_msg)
                    stats['errors'] += 1
                    stats['error_messages'].append(error_msg)
                    continue

            # Commit all changes
            try:
                db.session.commit()
                logger.info(f"Worklog synchronization completed: {stats}")
            except Exception as e:
                db.session.rollback()
                error_msg = f"Failed to commit worklog changes: {str(e)}"
                logger.error(error_msg)
                stats['errors'] += 1
                stats['error_messages'].append(error_msg)
                raise

            return stats

        except Exception as e:
            error_msg = f"Worklog synchronization failed: {str(e)}"
            logger.error(error_msg)
            stats['errors'] += 1
            stats['error_messages'].append(error_msg)
            raise JiraConnectionError(error_msg)

    def sync_all(self) -> Tuple[bool, Dict[str, Any]]:
        """Synchronize all data from JIRA."""
        try:
            logger.info("Starting full JIRA synchronization")
            self.ensure_connected()
            
            results = {
                'users': None,
                'projects': None,
                'worklogs': None,
                'errors': []
            }
            
            # Sync users first
            try:
                results['users'] = self.sync_users()
                logger.info("Users sync completed")
            except Exception as e:
                error_msg = f"Error syncing users: {str(e)}"
                logger.error(error_msg)
                results['errors'].append(error_msg)
            
            # Then sync projects
            try:
                results['projects'] = self.sync_projects()
                logger.info("Projects sync completed")
            except Exception as e:
                error_msg = f"Error syncing projects: {str(e)}"
                logger.error(error_msg)
                results['errors'].append(error_msg)
            
            # Finally sync worklogs
            try:
                results['worklogs'] = self.sync_worklogs()
                logger.info("Worklogs sync completed")
            except Exception as e:
                error_msg = f"Error syncing worklogs: {str(e)}"
                logger.error(error_msg)
                results['errors'].append(error_msg)
            
            success = all([
                results['users'] is not None,
                results['projects'] is not None,
                results['worklogs'] is not None
            ])
            
            if success:
                logger.info("Full sync completed successfully")
            else:
                logger.warning("Full sync completed with errors")
            
            return success, results
            
        except Exception as e:
            logger.error(f"Error during full sync: {str(e)}")
            return False, {'error': str(e)}

def get_jira_service() -> Optional[JiraService]:
    """Get JIRA service singleton instance."""
    try:
        return JiraService()
    except Exception as e:
        logger.error(f"Error getting JIRA service: {str(e)}")
        return None

def with_jira_error_handling(func):
    """Decorator for handling JIRA API errors."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except JIRAError as e:
            logger.error(f"JIRA API error in {func.__name__}: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {str(e)}")
            raise
    return wrapper

@contextmanager
def app_context():
    """Context manager to ensure we have application context."""
    if not current_app:
        from app import create_app
        app = create_app()
        ctx = app.app_context()
        ctx.push()
        try:
            yield
        finally:
            ctx.pop()
    else:
        yield

def init_jira_service(app):
    """Initialize JIRA service."""
    global _jira_instance, _is_initializing
    
    # Prevent recursive initialization
    if _is_initializing:
        return
        
    try:
        _is_initializing = True
        
        # Clear existing instance
        _jira_instance = None

        # Check if JIRA is configured
        if not all([
            app.config.get('JIRA_URL'),
            app.config.get('JIRA_USERNAME'),
            app.config.get('JIRA_API_TOKEN')
        ]):
            logger.info("JIRA integration is disabled - missing configuration")
            return

        # Log configuration once
        logger.info("=== JIRA Config Values ===")
        logger.info(f"URL: {app.config['JIRA_URL']}")
        logger.info(f"Username: {app.config['JIRA_USERNAME']}")
        logger.info(f"API Token exists: {bool(app.config['JIRA_API_TOKEN'])}")

    except Exception as e:
        logger.error(f"Error initializing JIRA service: {str(e)}")
    finally:
        _is_initializing = False

def get_jira_issues(jql: str) -> List[Dict]:
    """Pobiera zgłoszenia z Jiry na podstawie JQL."""
    jira_service = get_jira_service()
    return jira_service.jira.search_issues(jql)

def get_jira_project_metrics(project_key: str, start_date: datetime, end_date: datetime) -> Dict:
    """Pobiera metryki projektu."""
    jira_service = get_jira_service()
    jql = f'project = {project_key} AND created >= "{start_date.strftime("%Y-%m-%d")}" AND created <= "{end_date.strftime("%Y-%m-%d")}"'
    issues = get_jira_issues(jql)

    metrics = {
        'total_issues': len(issues),
        'by_type': {},
        'by_priority': {},
        'by_status': {},
        'by_assignee': {},
        'resolution_time': [],
        'created_vs_resolved': {
            'created': 0,
            'resolved': 0
        }
    }

    for issue in issues:
        # Liczenie według typu
        issue_type = issue['issue_type']
        metrics['by_type'][issue_type] = metrics['by_type'].get(issue_type, 0) + 1

        # Liczenie według priorytetu
        priority = issue['priority'] or 'No Priority'
        metrics['by_priority'][priority] = metrics['by_priority'].get(priority, 0) + 1

        # Liczenie według statusu
        status = issue['status']
        metrics['by_status'][status] = metrics['by_status'].get(status, 0) + 1

        # Liczenie według przypisanego
        assignee = issue['assignee'] or 'Unassigned'
        metrics['by_assignee'][assignee] = metrics['by_assignee'].get(assignee, 0) + 1

        # Czas rozwiązania
        if issue['resolved']:
            created = datetime.strptime(issue['created'].split('T')[0], '%Y-%m-%d')
            resolved = datetime.strptime(issue['resolved'].split('T')[0], '%Y-%m-%d')
            resolution_days = (resolved - created).days
            metrics['resolution_time'].append(resolution_days)

        # Utworzone vs Rozwiązane
        metrics['created_vs_resolved']['created'] += 1
        if issue['resolution']:
            metrics['created_vs_resolved']['resolved'] += 1

    # Oblicz średni czas rozwiązania
    if metrics['resolution_time']:
        metrics['avg_resolution_time'] = sum(metrics['resolution_time']) / len(metrics['resolution_time'])
    else:
        metrics['avg_resolution_time'] = 0

    return metrics

def get_jira_user_workload(user_name: str, start_date: datetime, end_date: datetime) -> Dict:
    """Pobiera obciążenie użytkownika."""
    jira_service = get_jira_service()
    jql = f'assignee = "{user_name}" AND updated >= "{start_date.strftime("%Y-%m-%d")}" AND updated <= "{end_date.strftime("%Y-%m-%d")}"'
    issues = get_jira_issues(jql)

    workload = {
        'total_issues': len(issues),
        'by_status': {},
        'by_priority': {},
        'daily_activity': {},
        'avg_resolution_time': 0,
        'resolution_rate': 0
    }

    resolved_count = 0
    resolution_times = []

    for issue in issues:
        # Liczenie według statusu
        status = issue['status']
        workload['by_status'][status] = workload['by_status'].get(status, 0) + 1

        # Liczenie według priorytetu
        priority = issue['priority'] or 'No Priority'
        workload['by_priority'][priority] = workload['by_priority'].get(priority, 0) + 1

        # Aktywność dzienna
        updated = issue['updated'].split('T')[0]
        workload['daily_activity'][updated] = workload['daily_activity'].get(updated, 0) + 1

        # Czas rozwiązania i współczynnik
        if issue['resolved']:
            resolved_count += 1
            created = datetime.strptime(issue['created'].split('T')[0], '%Y-%m-%d')
            resolved = datetime.strptime(issue['resolved'].split('T')[0], '%Y-%m-%d')
            resolution_times.append((resolved - created).days)

    # Oblicz średni czas rozwiązania
    if resolution_times:
        workload['avg_resolution_time'] = sum(resolution_times) / len(resolution_times)

    # Oblicz współczynnik rozwiązania
    if workload['total_issues'] > 0:
        workload['resolution_rate'] = resolved_count / workload['total_issues']

    return workload

@cache.memoize(timeout=300)
def get_jira_users(start: int = 0, limit: int = 50) -> List[Dict]:
    """Pobiera listę użytkowników z Jiry."""
    jira_service = get_jira_service()
    try:
        users = []
        while True:
            batch = requests.get(f"{jira_service.jira.server}/rest/api/2/user/search", params={'startAt': start, 'maxResults': limit})
            batch.raise_for_status()
            batch_users = batch.json()['users']
            if not batch_users:
                break
            
            users.extend([{
                'account_id': user['accountId'],
                'display_name': user['displayName'],
                'email': user.get('emailAddress', ''),
                'active': user.get('active', True)
            } for user in batch_users])
            
            if len(batch_users) < limit:
                break
            
            start += limit

        logger.info(f"Successfully retrieved {len(users)} users from Jira")
        return users
    except Exception as e:
        logger.error(f"Failed to get users from Jira: {str(e)}")
        raise

def get_jira_user_groups(account_id: str) -> List[str]:
    """Pobiera grupy użytkownika z Jiry."""
    jira_service = get_jira_service()
    try:
        groups = requests.get(f"{jira_service.jira.server}/rest/api/2/user/groups", params={'accountId': account_id})
        groups.raise_for_status()
        return [group['name'] for group in groups.json()['groups']]
    except Exception as e:
        logger.error(f"Failed to get user groups from Jira: {str(e)}")
        return []

def get_jira_client(config):
    """Get JIRA client instance."""
    try:
        if not config:
            logger.warning("No JIRA configuration provided")
            return None
            
        # Create basic auth token
        auth = base64.b64encode(
            f"{config.username}:{config.api_token}".encode()
        ).decode()
        
        # Initialize JIRA client
        jira = JIRA(
            server=config.url,
            basic_auth=(config.username, config.api_token),
            options={
                'verify': current_app.config.get('VERIFY_SSL', True)
            }
        )
        
        return jira
        
    except Exception as e:
        logger.error(f"Error creating JIRA client: {str(e)}")
        logger.exception("Full traceback:")
        raise

def test_connection(config: dict) -> dict:
    """Test JIRA connection with provided credentials."""
    try:
        jira = JIRA(
            server=config['url'],
            basic_auth=(config['username'], config['password'])
        )
        # Test connection by making a simple request
        jira.myself()
        return {
            'success': True,
            'message': 'Connection successful'
        }
    except Exception as e:
        logger.error(f"JIRA connection test failed: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }

def get_jira_config() -> dict:
    """Get JIRA configuration from database."""
    config = {
        'url': Setting.get_value('JIRA_URL'),
        'username': Setting.get_value('JIRA_USERNAME'),
        'token': Setting.get_value('JIRA_TOKEN'),
        'enabled': Setting.get_value('JIRA_ENABLED', 'false').lower() == 'true'
    }
    return config

def sync_jira_users():
    """Synchronize users with JIRA."""
    try:
        with app_context():
            jira = get_jira_service()
            if not jira or not jira.is_connected:
                raise ValueError("Could not connect to JIRA")

            # Get all JIRA users
            users = jira.get_users()
            stats = {"added": 0, "updated": 0}

            for jira_user in users['values']:
                try:
                    from app.models.user import User
                    from app.models.role import Role

                    # Get or create user
                    user = User.query.filter_by(email=jira_user['emailAddress']).first()
                    
                    if user:
                        # Update existing user
                        user.display_name = jira_user['displayName']
                        user.jira_key = jira_user['key']
                        stats["updated"] += 1
                    else:
                        # Create new user
                        user = User(
                            username=jira_user['name'],
                            email=jira_user['emailAddress'],
                            display_name=jira_user['displayName'],
                            jira_key=jira_user['key'],
                            is_active=True
                        )
                        db.session.add(user)
                        stats["added"] += 1

                    # Add default role if needed
                    default_role = Role.query.filter_by(name='user').first()
                    if default_role and default_role not in user.roles:
                        user.roles.append(default_role)

                except Exception as e:
                    logger.error(f"Error processing user {jira_user['emailAddress']}: {str(e)}")
                    continue

            db.session.commit()
            logger.info(f"JIRA sync completed: {stats}")
            return stats

    except Exception as e:
        logger.error(f"Error syncing JIRA users: {str(e)}")
        db.session.rollback()
        raise

@cache.memoize(timeout=300)  # Cache na 5 minut
def get_jira_projects():
    """Get JIRA projects."""
    try:
        jira = get_jira_service()
        if not jira:
            return []
            
        response = make_jira_request(f"{jira.jira.server}/rest/api/2/project")
        
        if response.status_code != 200:
            logger.error(f"Failed to get projects: {response.status_code}")
            return []
            
        return response.json()
        
    except Exception as e:
        logger.error(f"Error getting JIRA projects: {str(e)}")
        return []

def sync_jira_data():
    """Synchronize TEZ projects from JIRA."""
    try:
        jira = get_jira_service()
        if not jira or not jira.is_connected:
            return False, "Brak aktywnej konfiguracji JIRA"

        headers = {
            'Authorization': f'Basic {jira.jira.basic_auth[0]}:{jira.jira.basic_auth[1]}',
            'Content-Type': 'application/json'
        }

        # Get projects
        response = requests.get(
            f"{jira.jira.server}/rest/api/2/project",
            headers=headers,
            verify=current_app.config.get('VERIFY_SSL', True)
        )

        if response.status_code != 200:
            return False, f"Błąd pobierania projektów: {response.status_code} - {response.text}"

        # Filter TEZ projects
        all_projects = response.json()
        tez_projects = [
            project for project in all_projects
            if project.get('projectCategory') and 
            project['projectCategory'].get('name') == 'TEZ'
        ]

        logger.info(f"Pobrano {len(tez_projects)} projektów TEZ")

        # Save to database
        for project in tez_projects:
            # Update or create project in database
            from app.models.project import Project
            db_project = Project.query.filter_by(jira_key=project['key']).first()
            if not db_project:
                db_project = Project(
                    jira_key=project['key'],
                    name=project['name'],
                    jira_id=project['id']
                )
                db.session.add(db_project)

        # Update last sync time
        config = JiraConfig.query.filter_by(is_active=True).first()
        if config:
            config.last_sync = datetime.utcnow()
            db.session.commit()

        return True, f"Synchronizacja zakończona pomyślnie. Pobrano {len(tez_projects)} projektów TEZ"

    except Exception as e:
        logger.error(f"Error syncing JIRA data: {str(e)}")
        return False, f"Błąd synchronizacji: {str(e)}"

def save_jira_config(config: dict) -> None:
    """Save JIRA configuration."""
    try:
        # Deactivate current config
        JiraConfig.query.update({'is_active': False})
        
        # Create new config
        new_config = JiraConfig(
            url=config['url'],
            username=config['username'],
            api_token=decrypt_password(config['password']),
            is_active=True
        )
        
        db.session.add(new_config)
        db.session.commit()
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error saving JIRA config: {str(e)}")
        raise

def make_jira_request(url: str, method: str = 'GET', **kwargs) -> requests.Response:
    """Make JIRA API request with safety checks."""
    if method != 'GET':
        logger.warning(f"Attempted non-GET request to JIRA: {method} {url}")
        raise ValueError("Only GET requests are allowed to JIRA")
        
    jira = get_jira_service()
    if not jira:
        raise ValueError("No JIRA configuration found")
        
    headers = {
        'Authorization': f'Basic {jira.jira.basic_auth[0]}:{jira.jira.basic_auth[1]}',
        'Content-Type': 'application/json'
    }
    
    return requests.request(
        method='GET',  # Wymuszamy GET
        url=url,
        headers=headers,
        verify=current_app.config.get('VERIFY_SSL', True),
        **kwargs
    )

def create_jira_client():
    """Create JIRA client with proper configuration."""
    try:
        options = {
            'server': current_app.config['JIRA_URL'],
            'verify': current_app.config.get('VERIFY_SSL', False),
            'timeout': current_app.config.get('JIRA_TIMEOUT', 30)
        }

        logger.info(f"JIRA connection options: {options}")
        logger.info(f"Environment variables: {dict(os.environ)}")

        # Dodaj więcej logowania
        response = requests.get(
            current_app.config['JIRA_URL'],
            verify=options['verify'],
            timeout=options['timeout']
        )
        logger.info(f"JIRA server response: {response.status_code}")
        
        # Reszta kodu...

    except Exception as e:
        logger.error(f"Error creating JIRA client: {str(e)}")
        logger.exception("Full traceback:")
        raise

# Eksportujemy tylko get_jira_service
__all__ = ['get_jira_service', 'get_jira_projects', 'sync_jira_data', 'test_connection', 'save_jira_config'] 