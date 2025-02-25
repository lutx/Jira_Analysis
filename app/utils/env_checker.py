import os
import logging

logger = logging.getLogger(__name__)

def check_jira_env_vars():
    """Check JIRA environment variables."""
    required_vars = ['JIRA_URL', 'JIRA_USERNAME', 'JIRA_API_TOKEN']
    optional_vars = ['JIRA_TIMEOUT', 'VERIFY_SSL', 'JIRA_ENABLED']
    
    logger.info("Checking JIRA environment variables...")
    
    # Check required vars with actual values
    for var in required_vars:
        value = os.environ.get(var)
        if not value:
            logger.error(f"Missing required variable: {var}")
            return False
        if var != 'JIRA_API_TOKEN':
            logger.info(f"{var} = {value}")
        else:
            logger.info(f"{var} exists: {bool(value)}")
    
    # Check if URL is correct
    jira_url = os.environ.get('JIRA_URL')
    if jira_url == 'https://your-domain.atlassian.net':
        logger.warning("JIRA_URL has default value!")
        return False
        
    return True 