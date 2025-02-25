from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from app.database import get_db
from app.extensions import db
import logging
from app.models.team_settings import TeamSettings
from sqlalchemy.orm import relationship
from app.models.team_membership import TeamMembership  # Import if needed
from sqlalchemy.exc import SQLAlchemyError, OperationalError

logger = logging.getLogger(__name__)

# Tabela asocjacyjna dla relacji team-project
team_projects = db.Table('team_projects',
    db.Column('team_id', db.Integer, db.ForeignKey('teams.id'), primary_key=True),
    db.Column('project_id', db.Integer, db.ForeignKey('projects.id'), primary_key=True),
    db.Column('created_at', db.DateTime, default=datetime.utcnow),
    extend_existing=True
)

class Team(db.Model):
    """Model for teams."""
    __tablename__ = 'teams'
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    leader_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Team leader
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    try:
        portfolio_id = db.Column(db.Integer, db.ForeignKey('portfolios.id'), nullable=True)  # Portfolio
        portfolio = db.relationship('Portfolio', backref='teams')
    except OperationalError:
        logger.warning("portfolio_id column not found in teams table")
        portfolio_id = None
        portfolio = None
    
    # Relacje
    leader = db.relationship('app.models.user.User', foreign_keys=[leader_id], backref='led_teams')
    team_members = db.relationship(
        'app.models.team_membership.TeamMembership',
        back_populates='team',
        cascade='all, delete-orphan'
    )
    assigned_projects = db.relationship(
        'Project',
        secondary='team_projects',
        back_populates='assigned_teams',
        lazy='dynamic'
    )

    def __repr__(self):
        return f'<Team {self.name}>'

    def to_dict(self):
        try:
            portfolio_data = {
                'portfolio_id': self.portfolio_id,
                'portfolio_name': self.portfolio.name if self.portfolio else None
            }
        except (OperationalError, AttributeError):
            portfolio_data = {
                'portfolio_id': None,
                'portfolio_name': None
            }
            
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'leader_id': self.leader_id,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'members_count': len(self.team_members),
            'projects_count': self.assigned_projects.count(),
            **portfolio_data
        }

    def get_settings(self):
        """Get team settings."""
        settings = TeamSettings.query.filter_by(team_id=self.id).first()
        if not settings:
            settings = TeamSettings(team_id=self.id)
            db.session.add(settings)
            db.session.commit()
        return settings.to_dict()

    def get_work_schedule(self):
        """Get team work schedule."""
        settings = self.get_settings()
        return {
            'default_work_hours': settings['default_work_hours'],
            'work_days': settings['work_days']
        }

    def is_work_day(self, date: datetime) -> bool:
        """Check if given date is a work day."""
        settings = self.get_settings()
        return date.isoweekday() in settings['work_days']

    @staticmethod
    def get_all(include_inactive: bool = False) -> List['Team']:
        """Pobiera wszystkie zespoły."""
        if include_inactive:
            return Team.query.order_by(Team.name).all()
        return Team.query.filter_by(is_active=True).order_by(Team.name).all()

    @staticmethod
    def get_by_id(team_id: int) -> Optional['Team']:
        """Pobiera zespół po ID."""
        return Team.query.get(team_id)

    def save(self) -> 'Team':
        """Zapisuje lub aktualizuje zespół."""
        db.session.add(self)
        db.session.commit()
        return self

    @property
    def members(self):
        """Get team members."""
        return [membership.user for membership in self.team_members]

    def add_member(self, user, role='member'):
        """Add a user to the team."""
        try:
            # Check if user is already a member
            existing_membership = next(
                (m for m in self.team_members if m.user_id == user.id),
                None
            )
            
            if existing_membership:
                logger.warning(f"User {user.username} is already a member of team {self.name}")
                return None
            
            # Create new membership
            from app.models.team_membership import TeamMembership
            membership = TeamMembership(team=self, user=user, role=role)
            
            try:
                db.session.add(membership)
                db.session.flush()  # Test if the membership can be added
                logger.info(f"Added user {user.username} to team {self.name} with role {role}")
                return membership
            except SQLAlchemyError as e:
                db.session.rollback()
                logger.error(f"Database error adding member to team: {str(e)}")
                return None
            
        except Exception as e:
            logger.error(f"Error adding member to team: {str(e)}")
            return None

    def remove_member(self, user):
        """Remove a user from the team."""
        membership = next((m for m in self.team_members if m.user_id == user.id), None)
        if membership:
            db.session.delete(membership)
            return True
        return False

    @property
    def users(self):
        """Get team's users."""
        return self.members

    def get_activity_percentage(self) -> float:
        """Oblicza procent aktywności zespołu."""
        try:
            from app.models import Worklog
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            
            active_members_count = self.users.count()
            if not active_members_count:
                return 0
            
            expected_hours = active_members_count * 8 * 20  # 20 dni roboczych * 8h
            
            total_hours = db.session.query(
                db.func.sum(Worklog.time_spent)
            ).join(
                TeamMembership, TeamMembership.user_id == Worklog.user_id
            ).filter(
                TeamMembership.team_id == self.id,
                Worklog.date.between(start_date, end_date)
            ).scalar() or 0
            
            return round((total_hours / expected_hours) * 100, 2) if expected_hours > 0 else 0
            
        except Exception as e:
            logger.error(f"Error calculating team activity: {str(e)}")
            return 0

    def update_settings(self, settings: Dict[str, Any]) -> None:
        """Aktualizuje ustawienia zespołu."""
        db.session.query(TeamSettings).filter_by(team_id=self.id).update(settings)
        db.session.commit()

    def get_expected_hours(self, start_date: datetime, end_date: datetime) -> float:
        """Oblicza oczekiwaną liczbę godzin pracy w danym okresie."""
        settings = self.get_settings()
        total_hours = 0
        current_date = start_date
        
        while current_date <= end_date:
            if self.is_work_day(current_date):
                total_hours += settings['default_work_hours']
            current_date += timedelta(days=1)
        
        return total_hours

    def get_workload(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Oblicza obciążenie zespołu w danym okresie."""
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute("""
            SELECT user_name, SUM(time_spent) as total_hours
            FROM worklogs
            WHERE user_name IN (
                SELECT user_name FROM team_memberships WHERE team_id = ?
            )
            AND work_date BETWEEN ? AND ?
            GROUP BY user_name
        """, (
            self.id,
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d')
        ))
        
        results = cursor.fetchall()
        expected_hours = self.get_expected_hours(start_date, end_date)
        
        workload = {
            'expected_hours': expected_hours,
            'users': {}
        }
        
        for row in results:
            workload['users'][row['user_name']] = {
                'hours': row['total_hours'],
                'percentage': (row['total_hours'] / expected_hours * 100) if expected_hours > 0 else 0
            }
        
        return workload

    def get_activity(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Pobiera raport aktywności zespołu."""
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute("""
            SELECT 
                DATE(work_date) as date,
                SUM(time_spent) as hours,
                COUNT(DISTINCT issue_key) as tasks
            FROM worklogs
            WHERE user_name IN (
                SELECT user_name FROM team_memberships WHERE team_id = ?
            )
            AND work_date BETWEEN ? AND ?
            GROUP BY DATE(work_date)
            ORDER BY date
        """, (
            self.id,
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d')
        ))
        
        results = cursor.fetchall()
        
        activity = {
            'daily_activity': {},
            'tasks': {},
            'total_hours': 0,
            'total_tasks': 0,
            'avg_daily_hours': 0
        }
        
        for row in results:
            activity['daily_activity'][row['date']] = row['hours']
            activity['tasks'][row['date']] = row['tasks']
            activity['total_hours'] += row['hours']
            activity['total_tasks'] += row['tasks']
        
        days = len(results)
        if days > 0:
            activity['avg_daily_hours'] = activity['total_hours'] / days
        
        return activity

    def get_efficiency(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Pobiera raport efektywności zespołu."""
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute("""
            SELECT 
                user_name,
                SUM(time_spent) as hours,
                COUNT(DISTINCT issue_key) as tasks
            FROM worklogs
            WHERE user_name IN (
                SELECT user_name FROM team_memberships WHERE team_id = ?
            )
            AND work_date BETWEEN ? AND ?
            GROUP BY user_name
        """, (
            self.id,
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d')
        ))
        
        results = cursor.fetchall()
        
        efficiency = {
            'users': {},
            'total_hours': 0,
            'total_tasks': 0,
            'avg_efficiency': 0
        }
        
        for row in results:
            user = row['user_name']
            hours = row['hours']
            tasks = row['tasks']
            
            efficiency['users'][user] = {
                'hours': hours,
                'tasks': tasks,
                'efficiency': (tasks / hours * 100) if hours > 0 else 0
            }
            
            efficiency['total_hours'] += hours
            efficiency['total_tasks'] += tasks
        
        if efficiency['total_hours'] > 0:
            efficiency['avg_efficiency'] = efficiency['total_tasks'] / efficiency['total_hours'] * 100
        
        return efficiency

    def get_member_stats(self, user_name: str, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Pobiera statystyki członka zespołu."""
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute("""
            SELECT 
                DATE(work_date) as date,
                SUM(time_spent) as hours,
                COUNT(DISTINCT issue_key) as tasks,
                GROUP_CONCAT(DISTINCT project_key) as projects
            FROM worklogs
            WHERE user_name = ?
            AND work_date BETWEEN ? AND ?
            GROUP BY DATE(work_date)
            ORDER BY date
        """, (
            user_name,
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d')
        ))
        
        results = cursor.fetchall()
        
        stats = {
            'daily_stats': {},
            'total_hours': 0,
            'total_tasks': 0,
            'projects': set(),
            'avg_daily_hours': 0,
            'avg_tasks_per_day': 0
        }
        
        for row in results:
            stats['daily_stats'][row['date']] = {
                'hours': row['hours'],
                'tasks': row['tasks'],
                'projects': row['projects'].split(',') if row['projects'] else []
            }
            stats['total_hours'] += row['hours']
            stats['total_tasks'] += row['tasks']
            if row['projects']:
                stats['projects'].update(row['projects'].split(','))
        
        days = len(results)
        if days > 0:
            stats['avg_daily_hours'] = stats['total_hours'] / days
            stats['avg_tasks_per_day'] = stats['total_tasks'] / days
        
        stats['projects'] = list(stats['projects'])
        
        return stats

    def get_project_stats(self, project_key: str, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Pobiera statystyki projektu dla zespołu."""
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute("""
            SELECT 
                user_name,
                SUM(time_spent) as hours,
                COUNT(DISTINCT issue_key) as tasks
            FROM worklogs
            WHERE project_key = ?
            AND user_name IN (
                SELECT user_name FROM team_memberships WHERE team_id = ?
            )
            AND work_date BETWEEN ? AND ?
            GROUP BY user_name
        """, (
            project_key,
            self.id,
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d')
        ))
        
        results = cursor.fetchall()
        
        stats = {
            'users': {},
            'total_hours': 0,
            'total_tasks': 0,
            'avg_hours_per_user': 0
        }
        
        for row in results:
            stats['users'][row['user_name']] = {
                'hours': row['hours'],
                'tasks': row['tasks']
            }
            stats['total_hours'] += row['hours']
            stats['total_tasks'] += row['tasks']
        
        user_count = len(stats['users'])
        if user_count > 0:
            stats['avg_hours_per_user'] = stats['total_hours'] / user_count
        
        return stats 

    @property
    def activity_percentage(self) -> float:
        """Property dla procentu aktywności."""
        return self.get_activity_percentage() 