from app.extensions import db
from datetime import datetime
import json

class TeamSettings(db.Model):
    __tablename__ = 'team_settings'
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False, unique=True)
    default_work_hours = db.Column(db.Integer, default=8)
    work_days = db.Column(db.String(100), default='[1,2,3,4,5]')  # JSON array of weekdays
    notifications = db.Column(db.Text, default='{}')  # JSON object
    integrations = db.Column(db.Text, default='{}')  # JSON object
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'team_id': self.team_id,
            'default_work_hours': self.default_work_hours,
            'work_days': json.loads(self.work_days),
            'notifications': json.loads(self.notifications),
            'integrations': json.loads(self.integrations),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        } 