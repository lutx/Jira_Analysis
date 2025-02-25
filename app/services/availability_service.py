from app.models import UserAvailability
from app.extensions import db
from datetime import datetime
import calendar
import logging
from typing import Dict, Any
from sqlalchemy import extract

logger = logging.getLogger(__name__)

def calculate_working_days(month_year: str) -> int:
    """Calculate working days in a month excluding weekends."""
    try:
        year, month = map(int, month_year.split('-'))
        cal = calendar.monthcalendar(year, month)
        working_days = sum(1 for week in cal for day in week[0:5] if day != 0)
        return working_days
    except Exception as e:
        logger.error(f"Error calculating working days: {str(e)}")
        return 0

def get_user_availability(user_id: int, month_year: str) -> dict:
    """Get user availability for a given month."""
    try:
        availability = UserAvailability.query.filter_by(
            user_id=user_id,
            month_year=month_year
        ).first()
        
        if not availability:
            working_days = calculate_working_days(month_year)
            availability = UserAvailability(
                user_id=user_id,
                month_year=month_year,
                working_days=working_days
            )
            db.session.add(availability)
            db.session.commit()
        
        return availability.to_dict()
    except Exception as e:
        logger.error(f"Error getting user availability: {str(e)}")
        return {
            'working_days': 0,
            'holidays': 0,
            'leave_days': 0,
            'available_days': 0
        }

def calculate_user_availability(user_id: int, month: datetime) -> Dict[str, Any]:
    """Calculate user availability for given month."""
    try:
        # Get working days in month
        working_days = get_working_days_in_month(month)
        
        # Get user leaves
        leaves = UserAvailability.query.filter(
            UserAvailability.user_id == user_id,
            extract('month', UserAvailability.date) == month.month,
            extract('year', UserAvailability.date) == month.year
        ).all()
        
        # Calculate available hours
        total_hours = working_days * 8  # 8h workday
        leave_hours = sum(leave.available_hours for leave in leaves)
        available_hours = total_hours - leave_hours
        
        return {
            'total_hours': total_hours,
            'leave_hours': leave_hours,
            'available_hours': available_hours,
            'availability_percentage': (available_hours / total_hours) * 100
        }
    except Exception as e:
        logger.error(f"Error calculating availability: {str(e)}")
        return None

def get_working_days_in_month(month: datetime) -> int:
    """Get number of working days in month."""
    cal = calendar.monthcalendar(month.year, month.month)
    return sum(1 for week in cal for day in week[0:5] if day != 0) 