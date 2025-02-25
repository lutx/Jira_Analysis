import click
from flask.cli import with_appcontext
from app.services.jira_sync import JiraSync

@click.group()
def jira():
    """JIRA synchronization commands."""
    pass

@jira.command()
@with_appcontext
def sync_all():
    """Synchronize all JIRA data."""
    jira_sync = JiraSync()
    click.echo("Starting JIRA synchronization...")
    
    if jira_sync.sync_users():
        click.echo("Users synchronized successfully")
    else:
        click.echo("Failed to synchronize users")
        
    if jira_sync.sync_projects():
        click.echo("Projects synchronized successfully")
    else:
        click.echo("Failed to synchronize projects")
        
    if jira_sync.sync_worklogs():
        click.echo("Worklogs synchronized successfully")
    else:
        click.echo("Failed to synchronize worklogs")

@jira.command()
@with_appcontext
def sync_users():
    """Synchronize JIRA users."""
    jira_sync = JiraSync()
    if jira_sync.sync_users():
        click.echo("Users synchronized successfully")
    else:
        click.echo("Failed to synchronize users") 