from app.extensions import db
from datetime import datetime

class ProjectAssignment(db.Model):
    """Model reprezentujący przypisanie użytkownika do projektu."""
    __tablename__ = 'project_assignments'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=True)
    allocation = db.Column(db.Float, default=100.0)  # Procentowa alokacja do projektu
    is_active = db.Column(db.Boolean, default=True)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relacje
    project = db.relationship('Project', back_populates='assignments')
    user = db.relationship('User', back_populates='project_assignments')
    role = db.relationship('Role')
    
    def __repr__(self):
        return f'<ProjectAssignment {self.project_id}-{self.user_id}>'
        
    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'user_id': self.user_id,
            'role_id': self.role_id,
            'allocation': self.allocation,
            'is_active': self.is_active,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        } 