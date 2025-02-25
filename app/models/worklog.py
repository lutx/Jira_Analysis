from app.extensions import db
from datetime import datetime
from typing import Dict, Any, Optional
from app.database import get_db
from sqlalchemy.orm import relationship
import logging

logger = logging.getLogger(__name__)

class Worklog(db.Model):
    """Model reprezentujący wpis czasu pracy."""
    __tablename__ = 'worklogs'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    jira_worklog_id = db.Column(db.String(100), unique=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    issue_id = db.Column(db.Integer, db.ForeignKey('issues.id'), nullable=False)
    description = db.Column(db.Text)
    time_spent_seconds = db.Column(db.Integer, nullable=False)
    work_date = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_sync = db.Column(db.DateTime)

    # Relationships
    user = db.relationship('User', back_populates='worklogs')
    project = db.relationship('Project', back_populates='worklogs')
    issue = db.relationship('Issue', back_populates='worklogs')

    @property
    def time_spent_hours(self):
        """Convert time spent from seconds to hours."""
        return round(self.time_spent_seconds / 3600, 2) if self.time_spent_seconds else 0

    def __repr__(self):
        return f'<Worklog {self.id} - {self.user.username if self.user else "Unknown"} - {self.time_spent_hours}h>'

    def to_dict(self):
        """Convert worklog to dictionary."""
        try:
            return {
                'id': self.id,
                'jira_worklog_id': self.jira_worklog_id,
                'user': {
                    'id': self.user.id,
                    'username': self.user.username,
                    'display_name': self.user.display_name
                } if self.user else None,
                'project': {
                    'id': self.project.id,
                    'name': self.project.name,
                    'jira_key': self.project.jira_key
                } if self.project else None,
                'issue': {
                    'id': self.issue.id,
                    'jira_key': self.issue.jira_key,
                    'summary': self.issue.summary
                } if self.issue else None,
                'description': self.description,
                'time_spent_seconds': self.time_spent_seconds,
                'time_spent_hours': self.time_spent_hours,
                'work_date': self.work_date.strftime('%Y-%m-%d') if self.work_date else None,
                'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
                'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None,
                'last_sync': self.last_sync.strftime('%Y-%m-%d %H:%M:%S') if self.last_sync else None
            }
        except Exception as e:
            logger.error(f"Error converting worklog {self.id} to dict: {str(e)}")
            return {
                'id': self.id,
                'error': 'Error converting worklog to dictionary'
            }

    def save(self) -> bool:
        """Saves or updates the worklog in the database."""
        db = get_db()
        cursor = db.cursor()

        try:
            if self.id:
                # Update existing worklog
                cursor.execute("""
                    UPDATE worklogs 
                    SET user_id = ?, issue_id = ?, project_id = ?, description = ?, 
                        time_spent_seconds = ?, work_date = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (self.user_id, self.issue_id, self.project_id, self.description, 
                      self.time_spent_seconds, self.work_date, self.id))
            else:
                # Insert new worklog
                cursor.execute("""
                    INSERT INTO worklogs (user_id, issue_id, project_id, description, 
                                        time_spent_seconds, work_date)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (self.user_id, self.issue_id, self.project_id, self.description, 
                      self.time_spent_seconds, self.work_date))
                self.id = cursor.lastrowid

            db.commit()
            return True

        except Exception as e:
            db.rollback()
            raise e

    @staticmethod
    def get_by_id(worklog_id: int) -> Optional['Worklog']:
        """Retrieves a worklog by its ID."""
        db = get_db()
        cursor = db.cursor()

        cursor.execute("SELECT * FROM worklogs WHERE id = ?", (worklog_id,))
        row = cursor.fetchone()

        if row:
            return Worklog(
                id=row['id'],
                user_id=row['user_id'],
                issue_id=row['issue_id'],
                description=row['description'],
                time_spent_seconds=row['time_spent_seconds'],
                work_date=row['work_date'],
                created_at=datetime.strptime(row['created_at'], '%Y-%m-%d %H:%M:%S'),
                updated_at=datetime.strptime(row['updated_at'], '%Y-%m-%d %H:%M:%S')
            )
        return None

    @staticmethod
    def get_by_user(user_name: str, start_date: Optional[datetime] = None, 
                    end_date: Optional[datetime] = None) -> list['Worklog']:
        """Retrieves worklogs for a specific user within a date range."""
        db = get_db()
        cursor = db.cursor()

        query = "SELECT * FROM worklogs WHERE user_id IN (SELECT id FROM users WHERE name = ?) AND work_date BETWEEN ? AND ?"
        params = [user_name, start_date.strftime('%Y-%m-%d') if start_date else '1970-01-01', end_date.strftime('%Y-%m-%d') if end_date else '2100-01-01']

        cursor.execute(query, params)
        
        return [Worklog(
            id=row['id'],
            user_id=row['user_id'],
            issue_id=row['issue_id'],
            description=row['description'],
            time_spent_seconds=row['time_spent_seconds'],
            work_date=row['work_date'],
            created_at=datetime.strptime(row['created_at'], '%Y-%m-%d %H:%M:%S'),
            updated_at=datetime.strptime(row['updated_at'], '%Y-%m-%d %H:%M:%S')
        ) for row in cursor.fetchall()] 