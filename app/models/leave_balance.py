from app.extensions import db
from datetime import datetime
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class LeaveBalance(db.Model):
    """Model for tracking user leave balances."""
    __tablename__ = 'leave_balances'
    __table_args__ = (
        db.UniqueConstraint('user_id', 'year', name='uq_leave_balance_user_year'),
        {'extend_existing': True}
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    total_days = db.Column(db.Integer, default=26)  # Standard yearly allowance
    used_days = db.Column(db.Integer, default=0)
    pending_days = db.Column(db.Integer, default=0)  # Days in pending leave requests
    carried_over = db.Column(db.Integer, default=0)  # Days carried over from previous year
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = db.relationship('User', backref=db.backref('leave_balances', lazy='select'))

    def __repr__(self):
        return f'<LeaveBalance {self.user.username} - {self.year}>'

    def to_dict(self) -> Dict:
        """Convert leave balance to dictionary."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'year': self.year,
            'total_days': self.total_days,
            'used_days': self.used_days,
            'pending_days': self.pending_days,
            'carried_over': self.carried_over,
            'remaining_days': self.remaining_days,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    @property
    def remaining_days(self) -> int:
        """Calculate remaining leave days."""
        return self.total_days + self.carried_over - self.used_days - self.pending_days

    @classmethod
    def get_or_create(cls, user_id: int, year: Optional[int] = None) -> 'LeaveBalance':
        """Get or create leave balance for user and year."""
        if year is None:
            year = datetime.utcnow().year

        try:
            balance = cls.query.filter_by(user_id=user_id, year=year).first()
            if not balance:
                # Check for previous year's balance for carryover
                prev_balance = cls.query.filter_by(user_id=user_id, year=year-1).first()
                carried_over = min(prev_balance.remaining_days, 5) if prev_balance else 0

                balance = cls(
                    user_id=user_id,
                    year=year,
                    carried_over=carried_over
                )
                db.session.add(balance)
                db.session.commit()
                logger.info(f"Created new leave balance for user {user_id} year {year}")

            return balance
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error getting/creating leave balance: {str(e)}")
            raise

    def update_balance(self, days_change: int, is_pending: bool = False) -> bool:
        """Update leave balance when leave is requested/approved/rejected."""
        try:
            if is_pending:
                self.pending_days += days_change
            else:
                self.used_days += days_change
                self.pending_days = max(0, self.pending_days - abs(days_change))

            db.session.commit()
            logger.info(f"Updated leave balance for user {self.user_id}: {days_change} days")
            return True
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating leave balance: {str(e)}")
            return False

    def can_request_leave(self, days: int) -> bool:
        """Check if user can request leave for given number of days."""
        return self.remaining_days >= days 