from app.extensions import db
from datetime import datetime
from sqlalchemy import text, func
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Association table for many-to-many relationship between Portfolio and Project
portfolio_projects = db.Table(
    'portfolio_projects',
    db.Column('portfolio_id', db.Integer, db.ForeignKey('portfolios.id', ondelete='CASCADE')),
    db.Column('project_id', db.Integer, db.ForeignKey('projects.id', ondelete='CASCADE')),
    db.Column('created_at', db.DateTime, default=datetime.utcnow),
    extend_existing=True
)

class Portfolio(db.Model):
    """Portfolio model with enhanced analytics capabilities."""
    __tablename__ = 'portfolios'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    created_by = db.Column(db.String(255), nullable=True)

    # Relationships
    projects = db.relationship(
        'Project',
        secondary=portfolio_projects,
        backref=db.backref('portfolios', lazy='select'),
        lazy='select'
    )

    def __repr__(self):
        return f'<Portfolio {self.name}>'

    def to_dict(self):
        """Convert portfolio to dictionary with enhanced analytics."""
        base_dict = {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_active': self.is_active,
            'created_by': self.created_by,
            'projects_count': len(self.projects) if self.projects else 0,
            'project_statistics': self.get_project_statistics(),
        }

        # Add analytics data if requested
        try:
            base_dict.update({
                'role_distribution': self.get_role_distribution(),
                'hours_analysis': self.get_planned_vs_actual_hours()
            })
        except Exception as e:
            logger.warning(f"Could not add analytics data to portfolio dict: {str(e)}")

        return base_dict

    @property
    def active_projects(self):
        """Get active projects in portfolio."""
        return [p for p in self.projects if p.is_active]

    def add_project(self, project):
        """Add project to portfolio."""
        try:
            if project not in self.projects:
                self.projects.append(project)
                db.session.commit()
                logger.info(f"Added project {project.name} to portfolio {self.name}")
                return True
            return False
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error adding project to portfolio: {str(e)}")
            return False

    def remove_project(self, project):
        """Remove project from portfolio."""
        try:
            if project in self.projects:
                self.projects.remove(project)
                db.session.commit()
                logger.info(f"Removed project {project.name} from portfolio {self.name}")
                return True
            return False
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error removing project from portfolio: {str(e)}")
            return False

    @classmethod
    def migrate_schema(cls):
        """Migrate database schema to add required columns."""
        try:
            # Check if columns exist first
            inspector = db.inspect(db.engine)
            existing_columns = {col['name'] for col in inspector.get_columns('portfolios')}
            
            # Add columns one by one if they don't exist
            if 'is_active' not in existing_columns:
                db.session.execute(text("""
                    ALTER TABLE portfolios 
                    ADD COLUMN is_active BOOLEAN DEFAULT 1;
                """))
                logger.info("Added is_active column to portfolios table")
            
            if 'created_by' not in existing_columns:
                db.session.execute(text("""
                    ALTER TABLE portfolios 
                    ADD COLUMN created_by TEXT;
                """))
                logger.info("Added created_by column to portfolios table")
            
            # Update existing portfolios
            db.session.execute(text("""
                UPDATE portfolios SET is_active = 1 WHERE is_active IS NULL;
            """))
            
            # Create portfolio_projects table if it doesn't exist
            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS portfolio_projects (
                    portfolio_id INTEGER NOT NULL,
                    project_id INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (portfolio_id, project_id),
                    FOREIGN KEY (portfolio_id) REFERENCES portfolios(id) ON DELETE CASCADE,
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
                );
            """))
            
            db.session.commit()
            logger.info("Portfolio schema migration completed successfully")
            return True
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error migrating portfolio schema: {str(e)}")
            return False

    def get_role_distribution(self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> Dict[str, float]:
        """Get distribution of work hours by role within the portfolio."""
        try:
            from app.models.worklog import Worklog
            from app.models.user_role import UserRole
            
            query = db.session.query(
                UserRole.role_id,
                func.sum(Worklog.hours_spent).label('total_hours')
            ).join(
                Worklog, Worklog.user_id == UserRole.user_id
            ).filter(
                Worklog.project_id.in_([p.id for p in self.projects])
            )

            if start_date:
                query = query.filter(Worklog.date >= start_date)
            if end_date:
                query = query.filter(Worklog.date <= end_date)

            results = query.group_by(UserRole.role_id).all()
            
            # Convert role_ids to role names
            from app.models.role import Role
            role_hours = {}
            total_hours = 0
            
            for role_id, hours in results:
                role = Role.query.get(role_id)
                if role:
                    role_hours[role.name] = float(hours)
                    total_hours += float(hours)

            # Convert to percentages
            if total_hours > 0:
                return {role: (hours / total_hours) * 100 for role, hours in role_hours.items()}
            return role_hours

        except Exception as e:
            logger.error(f"Error getting role distribution for portfolio {self.name}: {str(e)}")
            return {}

    def get_planned_vs_actual_hours(self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> Dict[str, Dict[str, float]]:
        """Get planned vs actual hours for the portfolio."""
        try:
            from app.models.worklog import Worklog
            from app.models.project_assignment import ProjectAssignment

            # Get actual hours
            actual_query = db.session.query(
                func.sum(Worklog.hours_spent).label('actual_hours')
            ).filter(
                Worklog.project_id.in_([p.id for p in self.projects])
            )

            # Get planned hours
            planned_query = db.session.query(
                func.sum(ProjectAssignment.planned_hours).label('planned_hours')
            ).filter(
                ProjectAssignment.project_id.in_([p.id for p in self.projects])
            )

            if start_date:
                actual_query = actual_query.filter(Worklog.date >= start_date)
                planned_query = planned_query.filter(ProjectAssignment.start_date >= start_date)
            if end_date:
                actual_query = actual_query.filter(Worklog.date <= end_date)
                planned_query = planned_query.filter(ProjectAssignment.end_date <= end_date)

            actual_hours = actual_query.scalar() or 0
            planned_hours = planned_query.scalar() or 0

            return {
                'actual': float(actual_hours),
                'planned': float(planned_hours),
                'difference': float(actual_hours - planned_hours),
                'utilization': float(actual_hours / planned_hours * 100) if planned_hours > 0 else 0
            }

        except Exception as e:
            logger.error(f"Error getting planned vs actual hours for portfolio {self.name}: {str(e)}")
            return {'actual': 0, 'planned': 0, 'difference': 0, 'utilization': 0}

    def get_project_statistics(self) -> Dict[str, int]:
        """Get statistics about projects in the portfolio."""
        try:
            total_projects = len(self.projects)
            active_projects = len(self.active_projects)
            
            return {
                'total_projects': total_projects,
                'active_projects': active_projects,
                'inactive_projects': total_projects - active_projects
            }
        except Exception as e:
            logger.error(f"Error getting project statistics for portfolio {self.name}: {str(e)}")
            return {'total_projects': 0, 'active_projects': 0, 'inactive_projects': 0} 