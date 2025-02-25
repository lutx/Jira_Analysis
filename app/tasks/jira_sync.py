from app.extensions import celery
from app.services.jira_sync import JiraSync
from celery.schedules import crontab
import logging

logger = logging.getLogger(__name__)

@celery.task(name='app.tasks.sync_jira_data')
def sync_jira_data():
    """Celery task to synchronize all JIRA data."""
    try:
        from flask import current_app
        jira_sync = JiraSync(current_app._get_current_object())
        
        # Sync users
        if jira_sync.sync_users():
            logger.info("Successfully synchronized JIRA users")
        else:
            logger.error("Failed to synchronize JIRA users")

        # Sync projects
        if jira_sync.sync_projects():
            logger.info("Successfully synchronized JIRA projects")
        else:
            logger.error("Failed to synchronize JIRA projects")

        # Sync worklogs
        if jira_sync.sync_worklogs():
            logger.info("Successfully synchronized JIRA worklogs")
        else:
            logger.error("Failed to synchronize JIRA worklogs")

    except Exception as e:
        logger.error(f"Error in JIRA sync task: {str(e)}")
        raise

# Schedule the sync task to run every hour
@celery.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.add_periodic_task(
        crontab(hour='*'),  # Every hour
        sync_jira_data.s(),
        name='sync-jira-data'
    ) 