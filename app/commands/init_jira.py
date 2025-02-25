import click
from flask.cli import with_appcontext
from app.extensions import db
from app.models.jira_config import JiraConfig
from flask import current_app
import logging
import os

logger = logging.getLogger(__name__)

@click.command('init-jira')
@with_appcontext
def init_jira_command() -> None:
    """Inicjalizuje konfigurację JIRA z zmiennych środowiskowych."""
    try:
        jira_url = os.getenv('JIRA_URL')
        jira_username = os.getenv('JIRA_USERNAME')
        jira_api_token = os.getenv('JIRA_API_TOKEN')

        logger.info("=== JIRA Environment Variables ===")
        logger.info(f"JIRA_URL: {jira_url}")
        logger.info(f"JIRA_USERNAME: {jira_username}")
        logger.info(f"JIRA_API_TOKEN exists: {bool(jira_api_token)}")

        if not all([jira_url, jira_username, jira_api_token]):
            click.echo('Error: Missing required JIRA configuration')
            return

        config = JiraConfig.query.filter_by(is_active=True).first()
        if not config:
            config = JiraConfig()
            db.session.add(config)

        config.url = jira_url
        config.username = jira_username
        config.api_token = jira_api_token  # W przyszłości warto zaszyfrować token
        config.is_active = True

        db.session.commit()
        click.echo('JIRA configuration initialized successfully')

        # Test połączenia
        from app.services.jira_service import JiraService
        service = JiraService()
        success, message = service.test_connection()
        click.echo(f'Connection test: {message}')

    except Exception as e:
        click.echo(f'Error initializing JIRA configuration: {str(e)}')
        logger.exception("Error in init_jira_command")
        db.session.rollback() 