from app.extensions import db
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class UserRole(db.Model):
    """Model for user-role associations."""
    __tablename__ = 'user_roles'
    __table_args__ = (
        db.UniqueConstraint('user_id', 'role_id', name='uq_user_role'),
        db.Index('idx_user_roles_user_id', 'user_id'),
        db.Index('idx_user_roles_role_id', 'role_id'),
        {'extend_existing': True}
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id', ondelete='CASCADE'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = db.relationship('User', back_populates='user_roles', lazy='select')
    role = db.relationship('Role', back_populates='user_roles', lazy='select')

    def __init__(self, **kwargs):
        """Initialize user role association."""
        super().__init__(**kwargs)
        logger.info(f"Creating user role association: user_id={kwargs.get('user_id')}, role_id={kwargs.get('role_id')}")

    def __repr__(self):
        return f'<UserRole {self.user_id}:{self.role_id}>'

    def to_dict(self):
        """Convert to dictionary."""
        try:
            return {
                'id': self.id,
                'user_id': self.user_id,
                'role_id': self.role_id,
                'created_at': self.created_at.isoformat() if self.created_at else None,
                'updated_at': self.updated_at.isoformat() if self.updated_at else None
            }
        except Exception as e:
            logger.error(f"Error converting user role to dict: {str(e)}")
            return {} 