from app.extensions import db
from datetime import datetime
from sqlalchemy.orm import validates

class LeaveRequest(db.Model):
    __tablename__ = 'leave_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    user = db.relationship('User', 
                          foreign_keys=[user_id],
                          backref=db.backref('employee_leave_requests', lazy=True))
    
    approver = db.relationship('User',
                             foreign_keys=[approved_by],
                             backref=db.backref('approved_leave_requests', lazy=True))

    @validates('end_date')
    def validate_end_date(self, key, end_date):
        if end_date < self.start_date:
            raise ValueError('End date must be after start date')
        return end_date 

    @property
    def days(self):
        return (self.end_date - self.start_date).days + 1
        
    @property
    def status_class(self):
        return {
            'pending': 'warning',
            'approved': 'success',
            'rejected': 'danger'
        }.get(self.status, 'secondary')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'leave_type': self.type,
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'approved_by': self.approved_by,
            'user': self.user.to_dict() if self.user else None,
            'approver': self.approver.to_dict() if self.approver else None
        } 