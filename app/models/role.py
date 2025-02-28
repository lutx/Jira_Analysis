from app.extensions import db
from datetime import datetime
from sqlalchemy import func
import logging
import json
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class Role(db.Model):
    """Model for user roles with enhanced job functions and analytics."""
    __tablename__ = 'roles'
    __table_args__ = {'extend_existing': True}
    
    # Define job functions
    JOB_FUNCTIONS = {
        'developer': 'Software Developer',
        'qa': 'Quality Assurance',
        'pm': 'Project Manager',
        'ba': 'Business Analyst',
        'it': 'IT Support',
        'devops': 'DevOps Engineer',
        'designer': 'UI/UX Designer',
        'architect': 'Solution Architect',
        'team_lead': 'Team Lead',
        'scrum_master': 'Scrum Master'
    }
    
    # Define available permissions as class attribute
    PERMISSIONS = {
        'read': 'Read access',
        'write': 'Write access',
        'delete': 'Delete access',
        'admin': 'Admin access',
        'manage_teams': 'Team management',
        'manage_users': 'User management',
        'manage_projects': 'Project management',
        'manage_worklogs': 'Worklog management',
        'manage_settings': 'Settings management',
        'view_reports': 'View reports',
        'manage_reports': 'Report management',
        'manage_portfolios': 'Portfolio management',
        'manage_assignments': 'Assignment management',
        'view_analytics': 'View analytics',
        'manage_roles': 'Role management'
    }
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    description = db.Column(db.String(255))
    permissions = db.Column(db.String(1000))
    job_function = db.Column(db.String(50))  # New column for job function
    hourly_rate = db.Column(db.Float, default=0.0)  # New column for role-based cost tracking
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    users = db.relationship(
        'User',
        secondary='user_roles',
        primaryjoin='Role.id == UserRole.role_id',
        secondaryjoin='UserRole.user_id == User.id',
        back_populates='roles',
        lazy='select'
    )
    
    user_roles = db.relationship(
        'UserRole',
        back_populates='role',
        cascade='all, delete-orphan',
        lazy='select'
    )

    def __init__(self, **kwargs):
        """Initialize role with permissions and job function."""
        try:
            super().__init__(**kwargs)
            
            # Initialize permissions
            if 'permissions' in kwargs:
                if isinstance(kwargs['permissions'], (list, tuple)):
                    perms = [p for p in kwargs['permissions'] if p in self.PERMISSIONS]
                    self.set_permissions(perms)
                else:
                    self.set_permissions([])
            else:
                self.set_permissions([])
                
            # Initialize job function
            if 'job_function' in kwargs:
                if kwargs['job_function'] in self.JOB_FUNCTIONS:
                    self.job_function = kwargs['job_function']
                else:
                    logger.warning(f"Invalid job function: {kwargs['job_function']}")
                    
        except Exception as e:
            logger.error(f"Error initializing role {kwargs.get('name')}: {str(e)}")
            raise

    def get_permissions(self):
        """Get permissions list from JSON string."""
        try:
            if not self.permissions:
                return []
            return json.loads(self.permissions)
        except Exception as e:
            logger.error(f"Error getting permissions for role {self.name}: {str(e)}")
            return []

    def set_permissions(self, permissions_list):
        """Set permissions as JSON string."""
        try:
            if not permissions_list:
                self.permissions = '[]'
            else:
                self.permissions = json.dumps([p for p in permissions_list if p in self.PERMISSIONS])
        except Exception as e:
            logger.error(f"Error setting permissions for role {self.name}: {str(e)}")
            self.permissions = '[]'

    def has_permission(self, permission):
        """Check if role has specific permission."""
        try:
            perms = self.get_permissions()
            if not perms:
                logger.debug(f"Role {self.name} has no permissions")
                return False
            has_perm = permission in perms
            logger.debug(f"Checking permission {permission} for role {self.name}: {has_perm}")
            return has_perm
        except Exception as e:
            logger.error(f"Error checking permission {permission} for role {self.name}: {str(e)}")
            return False

    def __repr__(self):
        return f'<Role {self.name}>'

    def to_dict(self):
        """Convert role to dictionary with enhanced information."""
        try:
            base_dict = {
                'id': self.id,
                'name': self.name,
                'description': self.description,
                'permissions': self.get_permissions(),
                'job_function': self.job_function,
                'job_function_display': self.JOB_FUNCTIONS.get(self.job_function, self.job_function),
                'hourly_rate': self.hourly_rate,
                'created_at': self.created_at.isoformat() if self.created_at else None,
                'updated_at': self.updated_at.isoformat() if self.updated_at else None,
                'user_count': len(self.users)
            }

            # Add analytics if available
            try:
                base_dict.update({
                    'workload_statistics': self.get_workload_statistics(),
                    'project_distribution': self.get_project_distribution()
                })
            except Exception as e:
                logger.warning(f"Could not add analytics data to role dict: {str(e)}")

            return base_dict
        except Exception as e:
            logger.error(f"Error converting role {self.name} to dict: {str(e)}")
            return {}

    @classmethod
    def get_or_create_default_role(cls):
        """Get or create default user role."""
        try:
            role = cls.query.filter_by(name='user').first()
            if not role:
                role = cls(
                    name='user',
                    description='Default user role',
                    permissions=['read', 'write', 'view_reports']
                )
                db.session.add(role)
                db.session.commit()
                logger.info(f"Created default user role with permissions: {role.get_permissions()}")
            return role
        except Exception as e:
            logger.error(f"Error getting/creating default role: {str(e)}")
            db.session.rollback()
            return None

    @classmethod
    def create_superadmin_role(cls):
        """Create superadmin role with all permissions."""
        try:
            role = cls.query.filter_by(name='superadmin').first()
            if not role:
                permissions = list(cls.PERMISSIONS.keys())
                role = cls(
                    name='superadmin',
                    description='Superadmin role with all permissions',
                    permissions=permissions
                )
                db.session.add(role)
                db.session.commit()
                logger.info(f"Created superadmin role with permissions: {role.get_permissions()}")
            return role
        except Exception as e:
            logger.error(f"Error creating superadmin role: {str(e)}")
            db.session.rollback()
            return None

    @classmethod
    def get_available_permissions(cls):
        """Get list of available permissions."""
        return cls.PERMISSIONS

    def get_permission_display(self, permission_key):
        """Get display name for permission key."""
        return self.PERMISSIONS.get(permission_key, permission_key)

    def get_permissions_display(self):
        """Get human-readable permissions list."""
        try:
            return [self.PERMISSIONS.get(p, p) for p in (self.get_permissions() or [])]
        except Exception as e:
            logger.error(f"Error getting permissions display for role {self.name}: {str(e)}")
            return []

    def add_permission(self, permission):
        """Add permission to role."""
        try:
            perms = self.get_permissions()
            if permission in self.PERMISSIONS and permission not in perms:
                perms.append(permission)
                self.set_permissions(perms)
                logger.info(f"Added permission {permission} to role {self.name}")
                db.session.commit()
        except Exception as e:
            logger.error(f"Error adding permission {permission} to role {self.name}: {str(e)}")
            db.session.rollback()

    def remove_permission(self, permission):
        """Remove permission from role."""
        try:
            perms = self.get_permissions()
            if permission in perms:
                perms.remove(permission)
                self.set_permissions(perms)
                logger.info(f"Removed permission {permission} from role {self.name}")
                db.session.commit()
        except Exception as e:
            logger.error(f"Error removing permission {permission} from role {self.name}: {str(e)}")
            db.session.rollback()

    def get_workload_statistics(self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> Dict[str, float]:
        """Get workload statistics for this role."""
        try:
            from app.models.worklog import Worklog
            from app.models.user_role import UserRole
            
            query = db.session.query(
                func.sum(Worklog.hours_spent).label('total_hours'),
                func.count(func.distinct(Worklog.user_id)).label('active_users')
            ).join(
                UserRole, UserRole.user_id == Worklog.user_id
            ).filter(
                UserRole.role_id == self.id
            )

            if start_date:
                query = query.filter(Worklog.date >= start_date)
            if end_date:
                query = query.filter(Worklog.date <= end_date)

            result = query.first()
            
            return {
                'total_hours': float(result.total_hours or 0),
                'active_users': int(result.active_users or 0),
                'avg_hours_per_user': float(result.total_hours or 0) / int(result.active_users or 1) if result.active_users else 0,
                'total_cost': float(result.total_hours or 0) * self.hourly_rate
            }

        except Exception as e:
            logger.error(f"Error getting workload statistics for role {self.name}: {str(e)}")
            return {'total_hours': 0, 'active_users': 0, 'avg_hours_per_user': 0, 'total_cost': 0}

    def get_project_distribution(self) -> Dict[str, float]:
        """Get distribution of work across projects for this role."""
        try:
            from app.models.worklog import Worklog
            from app.models.user_role import UserRole
            from app.models.project import Project
            
            query = db.session.query(
                Project.name,
                func.sum(Worklog.hours_spent).label('hours')
            ).join(
                UserRole, UserRole.user_id == Worklog.user_id
            ).join(
                Project, Project.id == Worklog.project_id
            ).filter(
                UserRole.role_id == self.id
            ).group_by(
                Project.name
            )

            results = query.all()
            total_hours = sum(float(r.hours or 0) for r in results)
            
            if total_hours > 0:
                return {r.name: (float(r.hours or 0) / total_hours) * 100 for r in results}
            return {r.name: 0 for r in results}

        except Exception as e:
            logger.error(f"Error getting project distribution for role {self.name}: {str(e)}")
            return {} 