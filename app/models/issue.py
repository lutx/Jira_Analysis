from app.extensions import db
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class Issue(db.Model):
    """Model representing a JIRA issue."""
    __tablename__ = 'issues'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    jira_id = db.Column(db.String(100), unique=True)
    jira_key = db.Column(db.String(100), unique=True)
    summary = db.Column(db.String(500))
    description = db.Column(db.Text)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    status = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_sync = db.Column(db.DateTime)

    # Relationships
    project = db.relationship('Project', back_populates='issues')
    worklogs = db.relationship('Worklog', back_populates='issue', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Issue {self.jira_key}>'

    def to_dict(self):
        """Convert issue to dictionary."""
        try:
            return {
                'id': self.id,
                'jira_id': self.jira_id,
                'jira_key': self.jira_key,
                'summary': self.summary,
                'description': self.description,
                'status': self.status,
                'project': {
                    'id': self.project.id,
                    'name': self.project.name
                } if self.project else None,
                'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
                'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None,
                'last_sync': self.last_sync.strftime('%Y-%m-%d %H:%M:%S') if self.last_sync else None
            }
        except Exception as e:
            logger.error(f"Error converting issue {self.id} to dict: {str(e)}")
            return {
                'id': self.id,
                'error': 'Error converting issue to dictionary'
            }

    @classmethod
    def get_or_create(cls, jira_id: str, project_id: int, **kwargs):
        """Get existing issue or create new one."""
        issue = cls.query.filter_by(jira_id=jira_id).first()
        if not issue:
            issue = cls(jira_id=jira_id, project_id=project_id, **kwargs)
            db.session.add(issue)
            db.session.flush()
        return issue 