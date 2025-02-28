from app.extensions import db
from datetime import datetime
import logging
from typing import Dict, List, Optional
from sqlalchemy import func

logger = logging.getLogger(__name__)

class TeamCapacity(db.Model):
    """Model for tracking team capacity and workload."""
    __tablename__ = 'team_capacities'
    __table_args__ = (
        db.UniqueConstraint('team_id', 'year', 'month', name='uq_team_capacity_period'),
        {'extend_existing': True}
    )

    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    month = db.Column(db.Integer, nullable=False)
    working_days = db.Column(db.Integer, nullable=False)
    total_capacity = db.Column(db.Float)  # Total available hours
    allocated_capacity = db.Column(db.Float, default=0)  # Hours allocated to projects
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    team = db.relationship('Team', backref=db.backref('capacities', lazy='dynamic'))
    allocations = db.relationship('TeamAllocation', backref='capacity', lazy='dynamic')

    def __repr__(self):
        return f'<TeamCapacity {self.team.name} - {self.year}/{self.month}>'

    def to_dict(self) -> Dict:
        """Convert team capacity to dictionary."""
        return {
            'id': self.id,
            'team_id': self.team_id,
            'team_name': self.team.name,
            'year': self.year,
            'month': self.month,
            'working_days': self.working_days,
            'total_capacity': self.total_capacity,
            'allocated_capacity': self.allocated_capacity,
            'available_capacity': self.available_capacity,
            'utilization': self.utilization,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    @property
    def available_capacity(self) -> float:
        """Calculate available capacity in hours."""
        return self.total_capacity - self.allocated_capacity if self.total_capacity else 0

    @property
    def utilization(self) -> float:
        """Calculate capacity utilization percentage."""
        return (self.allocated_capacity / self.total_capacity * 100) if self.total_capacity else 0

    def calculate_total_capacity(self) -> float:
        """Calculate total capacity based on team members and working days."""
        try:
            from app.models.user import User
            from app.models.leave import Leave
            
            # Get all active team members
            team_members = User.query.filter_by(team_id=self.team_id, is_active=True).all()
            
            # Standard working hours per day
            hours_per_day = 8
            
            # Calculate base capacity
            base_capacity = len(team_members) * self.working_days * hours_per_day
            
            # Subtract planned leaves
            start_date = datetime(self.year, self.month, 1)
            if self.month == 12:
                end_date = datetime(self.year + 1, 1, 1)
            else:
                end_date = datetime(self.year, self.month + 1, 1)
            
            leaves = Leave.query.filter(
                Leave.user_id.in_([u.id for u in team_members]),
                Leave.status == 'approved',
                Leave.start_date < end_date,
                Leave.end_date >= start_date
            ).all()
            
            leave_days = sum(leave.duration for leave in leaves)
            capacity = base_capacity - (leave_days * hours_per_day)
            
            self.total_capacity = max(capacity, 0)
            db.session.commit()
            
            return self.total_capacity
            
        except Exception as e:
            logger.error(f"Error calculating team capacity: {str(e)}")
            return 0

    @classmethod
    def get_or_create(cls, team_id: int, year: int, month: int) -> 'TeamCapacity':
        """Get or create team capacity for given period."""
        try:
            capacity = cls.query.filter_by(
                team_id=team_id,
                year=year,
                month=month
            ).first()
            
            if not capacity:
                from app.models.holiday import Holiday
                from datetime import date
                import calendar
                
                # Calculate working days
                _, num_days = calendar.monthrange(year, month)
                start_date = date(year, month, 1)
                end_date = date(year, month, num_days)
                
                # Get holidays in the period
                holidays = Holiday.query.filter(
                    Holiday.date.between(start_date, end_date)
                ).count()
                
                # Calculate working days excluding weekends and holidays
                working_days = sum(1 for day in range(1, num_days + 1)
                                 if date(year, month, day).weekday() < 5)
                working_days -= holidays
                
                capacity = cls(
                    team_id=team_id,
                    year=year,
                    month=month,
                    working_days=working_days
                )
                db.session.add(capacity)
                db.session.commit()
                
                # Calculate initial capacity
                capacity.calculate_total_capacity()
            
            return capacity
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error getting/creating team capacity: {str(e)}")
            raise

class TeamAllocation(db.Model):
    """Model for tracking team allocations to projects."""
    __tablename__ = 'team_allocations'
    __table_args__ = (
        db.UniqueConstraint('capacity_id', 'project_id', name='uq_team_allocation_project'),
        {'extend_existing': True}
    )

    id = db.Column(db.Integer, primary_key=True)
    capacity_id = db.Column(db.Integer, db.ForeignKey('team_capacities.id', ondelete='CASCADE'))
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id', ondelete='CASCADE'))
    allocated_hours = db.Column(db.Float, default=0)
    priority = db.Column(db.Integer, default=1)  # Higher number = higher priority
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    project = db.relationship('Project')

    def __repr__(self):
        return f'<TeamAllocation {self.capacity.team.name} - {self.project.name}>'

    def to_dict(self) -> Dict:
        """Convert team allocation to dictionary."""
        return {
            'id': self.id,
            'capacity_id': self.capacity_id,
            'project_id': self.project_id,
            'project_name': self.project.name,
            'allocated_hours': self.allocated_hours,
            'priority': self.priority,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        } 