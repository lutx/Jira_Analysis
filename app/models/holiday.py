from app.extensions import db
from datetime import datetime
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class Holiday(db.Model):
    """Model for tracking holidays and non-working days."""
    __tablename__ = 'holidays'
    __table_args__ = (
        db.Index('idx_holiday_date', 'date'),
        db.UniqueConstraint('date', 'country_code', name='uq_holiday_date_country'),
        {'extend_existing': True}
    )

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    is_full_day = db.Column(db.Boolean, default=True)  # False for partial holidays
    country_code = db.Column(db.String(2), default='PL')  # ISO country code
    region = db.Column(db.String(50))  # For region-specific holidays
    type = db.Column(db.String(20), default='public')  # public, company, custom
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    is_recurring = db.Column(db.Boolean, default=False)  # For annual holidays

    def __repr__(self):
        return f'<Holiday {self.name} on {self.date}>'

    def to_dict(self) -> Dict:
        """Convert holiday to dictionary."""
        return {
            'id': self.id,
            'date': self.date.isoformat(),
            'name': self.name,
            'description': self.description,
            'is_full_day': self.is_full_day,
            'country_code': self.country_code,
            'region': self.region,
            'type': self.type,
            'is_recurring': self.is_recurring,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    @classmethod
    def get_holidays_in_range(cls, start_date: datetime, end_date: datetime, country_code: str = 'PL') -> List['Holiday']:
        """Get all holidays within a date range for a specific country."""
        try:
            return cls.query.filter(
                cls.date.between(start_date.date(), end_date.date()),
                cls.country_code == country_code
            ).order_by(cls.date).all()
        except Exception as e:
            logger.error(f"Error getting holidays in range: {str(e)}")
            return []

    @classmethod
    def is_holiday(cls, date: datetime, country_code: str = 'PL') -> bool:
        """Check if a specific date is a holiday."""
        try:
            return cls.query.filter(
                cls.date == date.date(),
                cls.country_code == country_code
            ).first() is not None
        except Exception as e:
            logger.error(f"Error checking if date is holiday: {str(e)}")
            return False

    @classmethod
    def import_holidays_from_csv(cls, file_path: str, created_by_id: Optional[int] = None) -> Dict[str, int]:
        """Import holidays from a CSV file."""
        import csv
        from datetime import datetime

        results = {'imported': 0, 'skipped': 0, 'errors': 0}
        
        try:
            with open(file_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    try:
                        # Parse date from CSV
                        date = datetime.strptime(row['date'], '%Y-%m-%d').date()
                        
                        # Check if holiday already exists
                        existing_holiday = cls.query.filter_by(
                            date=date,
                            country_code=row.get('country_code', 'PL')
                        ).first()
                        
                        if existing_holiday:
                            results['skipped'] += 1
                            continue
                        
                        # Create new holiday
                        holiday = cls(
                            date=date,
                            name=row['name'],
                            description=row.get('description'),
                            is_full_day=row.get('is_full_day', '1').lower() in ('1', 'true', 'yes'),
                            country_code=row.get('country_code', 'PL'),
                            region=row.get('region'),
                            type=row.get('type', 'public'),
                            is_recurring=row.get('is_recurring', '0').lower() in ('1', 'true', 'yes'),
                            created_by_id=created_by_id
                        )
                        
                        db.session.add(holiday)
                        results['imported'] += 1
                        
                    except Exception as e:
                        logger.error(f"Error importing holiday row: {str(e)}")
                        results['errors'] += 1
                        continue
                
                db.session.commit()
                logger.info(f"Holiday import completed: {results}")
                
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error importing holidays from CSV: {str(e)}")
            raise
            
        return results

    @classmethod
    def get_working_days(cls, start_date: datetime, end_date: datetime, country_code: str = 'PL') -> int:
        """Calculate number of working days between two dates, excluding holidays."""
        from datetime import timedelta
        
        working_days = 0
        current_date = start_date
        
        while current_date <= end_date:
            # Skip weekends
            if current_date.weekday() < 5:  # Monday = 0, Sunday = 6
                # Check if it's not a holiday
                if not cls.is_holiday(current_date, country_code):
                    working_days += 1
            current_date += timedelta(days=1)
            
        return working_days 