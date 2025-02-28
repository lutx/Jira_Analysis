import click
from flask.cli import with_appcontext
from app.models import User, LeaveBalance
from app.utils.email import send_leave_balance_reminder
import logging
from datetime import datetime
from typing import List, Dict

logger = logging.getLogger(__name__)

def get_users_with_high_balance(min_days: int = 10) -> List[Dict]:
    """Get users with high leave balance."""
    try:
        current_year = datetime.utcnow().year
        users_with_balance = []
        
        for user in User.query.filter_by(is_active=True).all():
            balance = LeaveBalance.get_or_create(user.id, current_year)
            if balance.remaining_days >= min_days:
                users_with_balance.append({
                    'user': user,
                    'balance': balance
                })
                
        return users_with_balance
    except Exception as e:
        logger.error(f"Error getting users with high balance: {str(e)}")
        return []

@click.command('send-leave-reminders')
@click.option('--min-days', default=10, help='Minimum remaining days to trigger reminder')
@with_appcontext
def send_leave_reminders_command(min_days: int):
    """Send reminders to users with high leave balance."""
    try:
        users_with_balance = get_users_with_high_balance(min_days)
        sent_count = 0
        
        for data in users_with_balance:
            user = data['user']
            balance = data['balance']
            
            if send_leave_balance_reminder(user.email, balance.to_dict()):
                sent_count += 1
                logger.info(f"Sent leave balance reminder to {user.email}")
            
        click.echo(f"Sent {sent_count} leave balance reminders")
    except Exception as e:
        logger.error(f"Error sending leave reminders: {str(e)}")
        click.echo(f"Error: {str(e)}")

def init_app(app):
    """Register the command with the Flask application."""
    app.cli.add_command(send_leave_reminders_command) 