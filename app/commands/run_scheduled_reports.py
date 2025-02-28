import click
from flask.cli import with_appcontext
from app.models import Report
from app.extensions import db
import logging
from datetime import datetime
from croniter import croniter

logger = logging.getLogger(__name__)

def should_run_report(report: Report) -> bool:
    """Check if a report should be run based on its schedule."""
    if not report.schedule or not report.last_run_at:
        return True
        
    try:
        cron = croniter(report.schedule, report.last_run_at)
        next_run = cron.get_next(datetime)
        return next_run <= datetime.utcnow()
    except Exception as e:
        logger.error(f"Error checking report schedule: {str(e)}")
        return False

@click.command('run-scheduled-reports')
@with_appcontext
def run_scheduled_reports_command():
    """Run all scheduled reports that are due."""
    try:
        reports = Report.query.filter(
            Report.is_active == True,
            Report.schedule.isnot(None)
        ).all()
        
        run_count = 0
        error_count = 0
        
        for report in reports:
            if should_run_report(report):
                try:
                    result = report.run()
                    if result and result.status == 'completed':
                        run_count += 1
                    else:
                        error_count += 1
                except Exception as e:
                    logger.error(f"Error running report {report.name}: {str(e)}")
                    error_count += 1
        
        click.echo(f"Ran {run_count} reports successfully, {error_count} failed")
    except Exception as e:
        logger.error(f"Error running scheduled reports: {str(e)}")
        click.echo(f"Error: {str(e)}")

def init_app(app):
    """Register the command with the Flask application."""
    app.cli.add_command(run_scheduled_reports_command) 