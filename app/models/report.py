from app.extensions import db
from datetime import datetime
import logging
from typing import Dict, List, Optional
import json

logger = logging.getLogger(__name__)

class Report(db.Model):
    """Model for storing report configurations and results."""
    __tablename__ = 'reports'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    report_type = db.Column(db.String(50), nullable=False)  # leave_usage, team_availability, cost_tracking, project_allocation
    parameters = db.Column(db.Text)  # JSON string of report parameters
    schedule = db.Column(db.String(100))  # Cron expression for scheduled reports
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_run_at = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)

    # Relationships
    created_by = db.relationship('User', backref=db.backref('reports', lazy='dynamic'))
    results = db.relationship('ReportResult', backref='report', lazy='dynamic')

    def __repr__(self):
        return f'<Report {self.name}>'

    def to_dict(self) -> Dict:
        """Convert report to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'report_type': self.report_type,
            'parameters': json.loads(self.parameters) if self.parameters else {},
            'schedule': self.schedule,
            'created_by': self.created_by.username if self.created_by else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'last_run_at': self.last_run_at.isoformat() if self.last_run_at else None,
            'is_active': self.is_active
        }

    def get_parameters(self) -> Dict:
        """Get report parameters as dictionary."""
        return json.loads(self.parameters) if self.parameters else {}

    def set_parameters(self, params: Dict) -> None:
        """Set report parameters from dictionary."""
        self.parameters = json.dumps(params)

    def run(self) -> Optional['ReportResult']:
        """Run the report and store results."""
        try:
            from app.services.report_service import generate_report
            result = generate_report(self)
            if result:
                self.last_run_at = datetime.utcnow()
                db.session.commit()
            return result
        except Exception as e:
            logger.error(f"Error running report {self.name}: {str(e)}")
            return None

class ReportResult(db.Model):
    """Model for storing report execution results."""
    __tablename__ = 'report_results'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.Integer, db.ForeignKey('reports.id', ondelete='CASCADE'))
    execution_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='pending')  # pending, running, completed, failed
    result_data = db.Column(db.Text)  # JSON string of report results
    error_message = db.Column(db.Text)
    execution_time = db.Column(db.Float)  # in seconds

    def __repr__(self):
        return f'<ReportResult {self.report_id} - {self.execution_date}>'

    def to_dict(self) -> Dict:
        """Convert report result to dictionary."""
        return {
            'id': self.id,
            'report_id': self.report_id,
            'execution_date': self.execution_date.isoformat() if self.execution_date else None,
            'status': self.status,
            'result_data': json.loads(self.result_data) if self.result_data else None,
            'error_message': self.error_message,
            'execution_time': self.execution_time
        }

    def set_result(self, data: Dict) -> None:
        """Set report result data."""
        self.result_data = json.dumps(data)
        self.status = 'completed'
        self.execution_time = (datetime.utcnow() - self.execution_date).total_seconds()

    def set_error(self, error_message: str) -> None:
        """Set error message for failed report."""
        self.error_message = error_message
        self.status = 'failed'
        self.execution_time = (datetime.utcnow() - self.execution_date).total_seconds() 