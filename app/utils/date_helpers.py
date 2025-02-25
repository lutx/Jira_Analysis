from datetime import datetime, timedelta
from typing import List, Tuple
import calendar

def get_date_range(start_date: datetime, end_date: datetime) -> List[datetime]:
    """Get list of dates between start_date and end_date."""
    date_list = []
    current_date = start_date
    
    while current_date <= end_date:
        date_list.append(current_date)
        current_date += timedelta(days=1)
        
    return date_list

def get_month_range(year: int, month: int) -> Tuple[datetime, datetime]:
    """Get first and last day of given month."""
    first_day = datetime(year, month, 1)
    last_day = datetime(year, month, calendar.monthrange(year, month)[1])
    return first_day, last_day

def get_week_range(date: datetime) -> Tuple[datetime, datetime]:
    """Get first and last day of week for given date."""
    start = date - timedelta(days=date.weekday())
    end = start + timedelta(days=6)
    return start, end

def get_quarter_range(year: int, quarter: int) -> Tuple[datetime, datetime]:
    """Get first and last day of given quarter."""
    first_month = 3 * quarter - 2
    last_month = 3 * quarter
    
    start_date = datetime(year, first_month, 1)
    end_date = datetime(year, last_month, calendar.monthrange(year, last_month)[1])
    
    return start_date, end_date

def get_year_range(year: int) -> Tuple[datetime, datetime]:
    """Get first and last day of given year."""
    start_date = datetime(year, 1, 1)
    end_date = datetime(year, 12, 31)
    return start_date, end_date

def format_date(date: datetime, format: str = '%Y-%m-%d') -> str:
    """Format date to string."""
    return date.strftime(format)

def parse_date(date_str: str, format: str = '%Y-%m-%d') -> datetime:
    """Parse date from string."""
    return datetime.strptime(date_str, format)

def get_working_days(start_date: datetime, end_date: datetime) -> int:
    """Get number of working days between dates (excluding weekends)."""
    days = get_date_range(start_date, end_date)
    return len([day for day in days if day.weekday() < 5])

def get_month_working_days(year: int, month: int) -> int:
    """Get number of working days in given month."""
    start_date, end_date = get_month_range(year, month)
    return get_working_days(start_date, end_date)

def is_working_day(date: datetime) -> bool:
    """Check if given date is a working day."""
    return date.weekday() < 5

def add_working_days(date: datetime, days: int) -> datetime:
    """Add given number of working days to date."""
    while days > 0:
        date += timedelta(days=1)
        if is_working_day(date):
            days -= 1
    return date

def subtract_working_days(date: datetime, days: int) -> datetime:
    """Subtract given number of working days from date."""
    while days > 0:
        date -= timedelta(days=1)
        if is_working_day(date):
            days -= 1
    return date 