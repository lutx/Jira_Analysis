from flask_apscheduler import APScheduler
from app.services.worklog_service import WorklogService
from app.services.jira_service import get_jira_service
from datetime import datetime
import logging
from flask import current_app
from app.extensions import scheduler

logger = logging.getLogger(__name__)
scheduler = APScheduler()

def init_scheduler(app):
    """Initialize the scheduler with the Flask app."""
    scheduler.init_app(app)
    scheduler.start()

    # Add scheduled jobs
    scheduler.add_job(
        id='sync_jira_worklogs',
        func=sync_jira_worklogs,
        trigger='interval',
        minutes=30,  # Sync every 30 minutes
        next_run_time=datetime.now()  # Run immediately on startup
    )

    scheduler.add_job(
        id='sync_jira_users',
        func=sync_jira_users,
        trigger='cron',
        hour=0  # Run daily at midnight
    )

    scheduler.add_job(
        id='sync_jira_data',
        func=sync_jira_data,
        trigger='cron',
        hour='*/4'
    )

@scheduler.task('interval', id='sync_jira_worklogs', minutes=30)
def sync_jira_worklogs():
    """Synchronize worklogs from Jira."""
    try:
        logger.info("Starting Jira worklog synchronization")
        stats = WorklogService.sync_jira_worklogs(days=30)
        logger.info(f"Jira worklog sync completed: {stats}")
    except Exception as e:
        logger.error(f"Error syncing Jira worklogs: {str(e)}")

@scheduler.task('cron', id='sync_jira_users', hour='0')
def sync_jira_users():
    """Synchronize users from JIRA daily at midnight."""
    try:
        logger.info("Starting JIRA user synchronization")
        jira = get_jira_service()
        stats = jira.sync_users()
        logger.info(f"JIRA user sync completed: {stats}")
    except Exception as e:
        logger.error(f"Error syncing JIRA users: {str(e)}", exc_info=True)

@scheduler.task('cron', id='sync_jira_data', hour='*/4')
def sync_jira_data():
    """Synchronize all JIRA data every 4 hours."""
    try:
        logger.info("Starting JIRA data synchronization")
        jira = get_jira_service()
        success, results = jira.sync_all()
        
        if success:
            logger.info("JIRA sync completed successfully")
            logger.info(f"Sync results: {results}")
        else:
            logger.error(f"JIRA sync failed: {results.get('error', 'Unknown error')}")
            
    except Exception as e:
        logger.error(f"Error in JIRA sync task: {str(e)}", exc_info=True)

@scheduler.task('cron', id='sync_jira_projects', hour='1')
def sync_jira_projects():
    """Synchronize projects from JIRA daily at 1 AM."""
    try:
        logger.info("Starting JIRA project synchronization")
        jira = get_jira_service()
        stats = jira.sync_projects()
        logger.info(f"JIRA project sync completed: {stats}")
    except Exception as e:
        logger.error(f"Error syncing JIRA projects: {str(e)}", exc_info=True)

def start_scheduler(app):
    """Start the scheduler with the Flask app."""
    init_scheduler(app)
    logger.info("Scheduler started successfully") 