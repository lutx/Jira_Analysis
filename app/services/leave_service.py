from flask import current_app
from app.models import Leave, User
from app.models.user import User
from app.models.team import Team
from app.models.team_membership import TeamMembership as TeamMember
from app.extensions import db
from datetime import datetime, timedelta
import logging
from app.services.availability_service import calculate_working_days
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

def get_user_leaves(user_id: int):
    """Get user's leaves."""
    return Leave.query.filter_by(user_id=user_id).all()

def create_leave_request(leave_data: dict):
    """Create new leave request."""
    try:
        leave = Leave(**leave_data)
        db.session.add(leave)
        db.session.commit()
        return True
    except Exception as e:
        logger.error(f"Error creating leave request: {str(e)}")
        db.session.rollback()
        return False

def update_leave_status(leave_id: int, status: str, approved_by: int = None) -> bool:
    """Update leave request status."""
    try:
        leave = Leave.query.get(leave_id)
        if not leave:
            return False

        leave.status = status
        if status == 'approved' and approved_by:
            leave.approved_by = approved_by
            leave.approve(approved_by)
        elif status == 'rejected' and approved_by:
            leave.reject(approved_by)
        
        db.session.commit()
        return True
        
    except Exception as e:
        logger.error(f"Error updating leave status: {str(e)}")
        db.session.rollback()
        return False

def delete_leave_request(leave_id: int) -> bool:
    """Delete leave request."""
    try:
        leave = Leave.query.get(leave_id)
        if leave:
            db.session.delete(leave)
            db.session.commit()
            return True
        return False
    except Exception as e:
        logger.error(f"Error deleting leave request: {str(e)}")
        db.session.rollback()
        return False

def get_team_leaves(team_id: int, start_date: datetime = None, end_date: datetime = None):
    """Get team leaves."""
    try:
        team = Team.query.get(team_id)
        if not team:
            logger.warning(f"Team {team_id} not found")
            return []
            
        team_members = TeamMember.query.filter_by(team_id=team_id).all()
        if not team_members:
            logger.warning(f"No members found for team {team_id}")
            return []
            
        member_ids = [member.user_id for member in team_members]
        query = Leave.query.filter(Leave.user_id.in_(member_ids))
        
        if start_date:
            query = query.filter(Leave.end_date >= start_date)
        if end_date:
            query = query.filter(Leave.start_date <= end_date)
            
        leaves = query.all()
        logger.info(f"Found {len(leaves)} leaves for team {team_id}")
        
        return leaves
        
    except Exception as e:
        logger.error(f"Error getting team leaves: {str(e)}")
        return []

def create_leave(leave_data: dict):
    """Create new leave."""
    return create_leave_request(leave_data)  # Alias dla istniejącej funkcji

def update_leave(leave_id: int, data: dict):
    """Update leave."""
    try:
        leave = Leave.query.get(leave_id)
        if not leave:
            return False

        for key, value in data.items():
            if hasattr(leave, key):
                setattr(leave, key, value)

        db.session.commit()
        return True
    except Exception as e:
        logger.error(f"Error updating leave: {str(e)}")
        db.session.rollback()
        return False

def delete_leave(leave_id: int):
    """Delete leave."""
    return delete_leave_request(leave_id)  # Alias dla istniejącej funkcji

def approve_leave(leave_id: int, approver_id: int):
    """Approve leave."""
    return update_leave_status(leave_id, 'approved', approver_id)

__all__ = [
    'get_user_leaves',
    'create_leave_request',
    'update_leave_status',
    'delete_leave_request',
    'get_team_leaves',
    'create_leave',
    'update_leave',
    'delete_leave',
    'approve_leave'
] 