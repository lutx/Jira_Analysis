from app.extensions import db
from datetime import datetime
from sqlalchemy.orm import relationship
from sqlalchemy import event

class Leave(db.Model):
    """Model for user leaves/absences."""
    __tablename__ = 'leaves'
    __table_args__ = (
        db.Index('idx_leave_user_id', 'user_id'),
        db.Index('idx_leave_start_date', 'start_date'),
        {'extend_existing': True}
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    leave_type = db.Column(db.String(50), nullable=False)  # vacation, sick, etc.
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    description = db.Column(db.Text)
    approved_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relacje
    user = db.relationship('User', foreign_keys=[user_id], back_populates='leaves')
    approver = db.relationship('User', foreign_keys=[approved_by_id], back_populates='approved_leaves')

    def __repr__(self):
        return f'<Leave {self.user.username} {self.start_date.date()} - {self.end_date.date()}>'

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'leave_type': self.leave_type,
            'status': self.status,
            'description': self.description,
            'approved_by_id': self.approved_by_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    @property
    def duration(self):
        """Get leave duration in days."""
        return (self.end_date - self.start_date).days + 1

    @property
    def is_approved(self):
        """Check if leave is approved."""
        return self.status == 'approved'

    @property
    def is_pending(self):
        """Check if leave is pending."""
        return self.status == 'pending'

    @property
    def is_rejected(self):
        """Check if leave is rejected."""
        return self.status == 'rejected'

    def approve(self, approver_id):
        """Approve leave request."""
        self.status = 'approved'
        self.approved_by_id = approver_id
        self.updated_at = datetime.utcnow()

    def reject(self, approver_id):
        """Reject leave request."""
        self.status = 'rejected'
        self.approved_by_id = approver_id
        self.updated_at = datetime.utcnow()

    def cancel(self):
        """Cancel leave request."""
        if self.is_pending:
            self.status = 'cancelled'
            self.updated_at = datetime.utcnow()
            return True
        return False

# Event listeners
@event.listens_for(Leave, 'before_insert')
def validate_dates(mapper, connection, target):
    """Validate leave dates before insert."""
    if target.start_date > target.end_date:
        raise ValueError("End date cannot be earlier than start date")

@event.listens_for(Leave, 'before_update')
def update_timestamp(mapper, connection, target):
    """Update timestamp on update."""
    target.updated_at = datetime.utcnow() 