from app.extensions import db
from datetime import datetime
from sqlalchemy import inspect, event
from flask import current_app

class AuditLog(db.Model):
    """Model for audit logs."""
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    action = db.Column(db.String(50), nullable=False)
    details = db.Column(db.Text)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)

    # Relations
    user = db.relationship('User', backref=db.backref('audit_logs', lazy=True))

    def __repr__(self):
        return f'<AuditLog {self.action}>'

    @staticmethod
    def log(action, user=None, details=None, ip_address=None, user_agent=None):
        """Create a new audit log entry."""
        try:
            log = AuditLog(
                user_id=user.id if user else None,
                action=action,
                details=details,
                ip_address=ip_address,
                user_agent=user_agent
            )
            db.session.add(log)
            db.session.commit()
            return log
        except Exception as e:
            current_app.logger.error(f"Error creating audit log: {str(e)}")
            db.session.rollback()
            return None

# Register event listener for database initialization
@event.listens_for(db.metadata, 'after_create')
def create_audit_logs_table(*args, **kwargs):
    """Create audit logs table after database initialization."""
    try:
        if not inspect(db.engine).has_table('audit_logs'):
            AuditLog.__table__.create(db.engine)
            if current_app:
                current_app.logger.info("Audit logs table created successfully")
    except Exception as e:
        if current_app:
            current_app.logger.error(f"Error creating audit logs table: {str(e)}")

def init_audit_logs(app):
    """Initialize audit logs - now just a placeholder for backwards compatibility."""
    pass 