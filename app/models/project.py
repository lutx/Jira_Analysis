from app.extensions import db
from datetime import datetime
from sqlalchemy import func
from sqlalchemy.orm import joinedload
import logging
from app.models.team_membership import TeamMembership

logger = logging.getLogger(__name__)

class Project(db.Model):
    """Project model."""
    __tablename__ = 'projects'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    jira_key = db.Column(db.String(10), unique=True)
    jira_id = db.Column(db.String(100), unique=True)
    status = db.Column(db.String(20), default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_sync = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)

    # Relationships
    issues = db.relationship('Issue', back_populates='project', cascade='all, delete-orphan')
    assignments = db.relationship('ProjectAssignment', back_populates='project', cascade='all, delete-orphan')
    
    # Worklog relationship through Issue
    worklogs = db.relationship(
        'Worklog',
        secondary='issues',
        primaryjoin='Project.id == Issue.project_id',
        secondaryjoin='Issue.id == Worklog.issue_id',
        viewonly=True
    )

    # Team relationship
    assigned_teams = db.relationship(
        'Team',
        secondary='team_projects',
        back_populates='assigned_projects',
        lazy='select'
    )

    def __repr__(self):
        return f'<Project {self.name}>'

    @property
    def total_hours(self):
        """Total hours spent on project."""
        if self.worklogs:
            return sum(worklog.time_spent_hours for worklog in self.worklogs)
        return 0

    @property
    def active_users_count(self):
        """Number of active users in project."""
        return self.assignments.filter_by(is_active=True).count()

    def to_dict(self):
        """Convert project to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'jira_key': self.jira_key,
            'jira_id': self.jira_id,
            'description': self.description,
            'status': self.status,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'last_sync': self.last_sync.isoformat() if self.last_sync else None
        }

    @property
    def active_assignments(self):
        """Get active project assignments."""
        return self.assignments.filter_by(is_active=True).all()

    def get_team_assignments(self, team_id: int):
        """Get project assignments for specific team."""
        return self.assignments.join(ProjectAssignment.user)\
            .join(User.team_members)\
            .filter(TeamMembership.team_id == team_id)\
            .all()

    def add_assignment(self, user_id: int, role_id: int, allocation: float = 100):
        """Add new project assignment."""
        assignment = ProjectAssignment(
            project_id=self.id,
            user_id=user_id,
            role_id=role_id,
            allocation=allocation
        )
        db.session.add(assignment)
        return assignment

    def remove_assignment(self, user_id: int):
        """Remove project assignment."""
        assignment = self.assignments.filter_by(user_id=user_id).first()
        if assignment:
            db.session.delete(assignment)
            return True
        return False

    @classmethod
    def get_project_with_stats(cls, project_id: int):
        """Get project with preloaded relationships and statistics."""
        return cls.query\
            .options(
                joinedload(cls.assigned_teams),
                joinedload(cls.assignments)
            )\
            .filter(cls.id == project_id)\
            .first() 