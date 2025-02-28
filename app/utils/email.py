from flask import current_app, render_template
from flask_mail import Message
from app.extensions import mail
import logging
from typing import List, Optional, Dict
from datetime import datetime

logger = logging.getLogger(__name__)

def send_email(subject: str, recipients: List[str], template: str, **kwargs) -> bool:
    """Send an email using a template."""
    try:
        msg = Message(
            subject=subject,
            recipients=recipients,
            sender=current_app.config['MAIL_DEFAULT_SENDER']
        )
        msg.html = render_template(template, **kwargs)
        mail.send(msg)
        logger.info(f"Email sent to {recipients}: {subject}")
        return True
    except Exception as e:
        logger.error(f"Error sending email: {str(e)}")
        return False

def send_leave_request_notification(leave: Dict, approvers: List[str]) -> bool:
    """Send notification about new leave request to approvers."""
    return send_email(
        subject="New Leave Request",
        recipients=approvers,
        template="emails/leave_request.html",
        leave=leave
    )

def send_leave_status_notification(leave: Dict, recipient: str) -> bool:
    """Send notification about leave request status change to the requester."""
    subject = f"Leave Request {leave['status'].title()}"
    return send_email(
        subject=subject,
        recipients=[recipient],
        template="emails/leave_status.html",
        leave=leave
    )

def send_leave_balance_reminder(user_email: str, balance: Dict) -> bool:
    """Send reminder about remaining leave balance."""
    return send_email(
        subject="Leave Balance Reminder",
        recipients=[user_email],
        template="emails/leave_balance.html",
        balance=balance
    )

def send_team_leave_notification(team_email: List[str], leave: Dict) -> bool:
    """Send notification about team member's approved leave to the team."""
    return send_email(
        subject=f"Team Leave Notification - {leave['user_name']}",
        recipients=team_email,
        template="emails/team_leave.html",
        leave=leave
    ) 