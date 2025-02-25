from app.extensions import db
from datetime import datetime

class TeamMembership(db.Model):
    """Model reprezentujący członkostwo w zespole."""
    __tablename__ = 'team_memberships'
    __table_args__ = (
        db.UniqueConstraint('team_id', 'user_id', name='uq_team_user'),
        {'extend_existing': True}
    )

    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    role = db.Column(db.String(50), default='member')  # member, leader, etc.
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships with back_populates
    team = db.relationship('app.models.team.Team', back_populates='team_members')
    user = db.relationship('app.models.user.User', back_populates='team_members')

    def __repr__(self):
        return f'<TeamMembership {self.user_id}-{self.team_id}>'

    def to_dict(self):
        return {
            'id': self.id,
            'team_id': self.team_id,
            'user_id': self.user_id,
            'role': self.role,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

# Alias dla kompatybilności wstecznej
TeamMember = TeamMembership 