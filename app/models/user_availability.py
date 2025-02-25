from app.extensions import db
from datetime import datetime

class UserAvailability(db.Model):
    """Model for user availability."""
    __tablename__ = 'user_availability'
    __table_args__ = (
        db.Index('idx_user_availability_date', 'user_id', 'date'),
        {'extend_existing': True}
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    hours_available = db.Column(db.Float, default=8.0)  # Domyślnie 8 godzin
    is_working_day = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relacje
    user = db.relationship('User', back_populates='availability')

    def __repr__(self):
        return f'<UserAvailability {self.user.username} {self.date.date()}>'

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'date': self.date.isoformat() if self.date else None,
            'hours_available': self.hours_available,
            'is_working_day': self.is_working_day,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    @property
    def available_days(self):
        """Oblicza liczbę dostępnych dni roboczych."""
        return self.working_days - (self.leave_days + self.sick_days + self.other_days)

    @property
    def availability_percentage(self):
        """Oblicza procent dostępności."""
        if self.working_days == 0:
            return 0
        return round((self.available_days / self.working_days) * 100, 2) 