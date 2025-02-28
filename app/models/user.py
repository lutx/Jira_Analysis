from flask_login import UserMixin
from app.extensions import db
from werkzeug.security import check_password_hash, generate_password_hash
import logging
from datetime import datetime
from sqlalchemy.orm import relationship
from typing import List, Optional
from app.models.role import Role
from flask import current_app
from app.models.user_role import UserRole
from app.models.worklog import Worklog
from app.models.team_membership import TeamMembership  # Import if needed

logger = logging.getLogger(__name__)

# Definicja tabeli asocjacyjnej dla user_projects
user_projects = db.Table('user_projects',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('project_id', db.Integer, db.ForeignKey('projects.id'), primary_key=True),
    db.Column('role', db.String(50), default='member'),
    db.Column('created_at', db.DateTime, default=datetime.utcnow),
    extend_existing=True
)

class User(UserMixin, db.Model):
    """User model."""
    __tablename__ = 'users'
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    display_name = db.Column(db.String(120))
    password_hash = db.Column(db.String(128))
    is_active = db.Column(db.Boolean, default=True)
    last_login = db.Column(db.DateTime)
    
    # JIRA fields
    jira_key = db.Column(db.String(64), unique=True, nullable=True)
    jira_display_name = db.Column(db.String(64), nullable=True)
    jira_email = db.Column(db.String(120), nullable=True)
    jira_active = db.Column(db.Boolean, nullable=True)
    jira_id = db.Column(db.String(100), unique=True, nullable=True)
    last_sync = db.Column(db.DateTime)
    last_jira_sync = db.Column(db.DateTime, nullable=True)
    jira_username = db.Column(db.String(80), unique=True, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Zmień nazwę kolumny z _is_superadmin na is_superadmin
    is_superadmin = db.Column(db.Boolean, default=False)  # Faktyczne pole w bazie danych

    # Relationships with explicit foreign keys
    roles = db.relationship(
        'Role',
        secondary='user_roles',
        primaryjoin='User.id == UserRole.user_id',
        secondaryjoin='UserRole.role_id == Role.id',
        back_populates='users',
        lazy='select'
    )
    
    user_roles = db.relationship(
        'UserRole',
        back_populates='user',
        cascade='all, delete-orphan',
        lazy='select'
    )

    project_assignments = db.relationship(
        'ProjectAssignment',
        back_populates='user',
        cascade='all, delete-orphan'
    )
    leaves = db.relationship(
        'Leave',
        foreign_keys='[Leave.user_id]',
        back_populates='user',
        lazy='dynamic'
    )
    approved_leaves = db.relationship(
        'Leave',
        foreign_keys='[Leave.approved_by_id]',
        back_populates='approver',
        lazy='dynamic'
    )
    worklogs = db.relationship('Worklog', back_populates='user', lazy='dynamic')
    availability = db.relationship('UserAvailability', back_populates='user', cascade='all, delete-orphan')
    tokens_blocklist = db.relationship(
        'TokenBlocklist',
        foreign_keys='[TokenBlocklist.user_id]',
        back_populates='user',
        lazy='dynamic'
    )
    revoked_tokens = db.relationship(
        'TokenBlocklist',
        foreign_keys='[TokenBlocklist.revoked_by_id]',
        back_populates='revoked_by',
        lazy='dynamic'
    )
    team_members = db.relationship(
        'app.models.team_membership.TeamMembership',
        back_populates='user',
        cascade='all, delete-orphan'
    )

    __table_args__ = (
        db.Index('idx_user_email', 'email'),
        db.Index('idx_user_jira_id', 'jira_id'),
    )

    def __init__(self, **kwargs):
        """Initialize user model."""
        try:
            super(User, self).__init__(**kwargs)
            
            # Only add default role if no roles specified and not superadmin
            if 'roles' not in kwargs and not kwargs.get('is_superadmin'):
                default_role = Role.get_or_create_default_role()
                if default_role:
                    self.roles.append(default_role)
                    logger.info(f"Added default role to user {kwargs.get('username')}")
            
            # Handle JIRA fields
            self.jira_key = kwargs.get('jira_key')
            self.jira_display_name = kwargs.get('jira_display_name')
            self.jira_email = kwargs.get('jira_email')
            self.jira_active = kwargs.get('jira_active')
            self.last_sync = kwargs.get('last_sync')
            self.jira_id = kwargs.get('jira_id')
            
        except Exception as e:
            logger.error(f"Error initializing user {kwargs.get('username')}: {str(e)}")
            raise

    def __repr__(self):
        return f'<User {self.username}>'

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Check password hash."""
        try:
            logger.debug(f"Checking password for user {self.username}")
            result = check_password_hash(self.password_hash, password)
            logger.debug(f"Password check result: {result}")
            return result
        except Exception as e:
            logger.error(f"Error checking password: {str(e)}")
            return False

    def to_dict(self) -> dict:
        """Return a dictionary representation of the user."""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'display_name': self.display_name,
            'is_active': self.is_active,
        }

    @property
    def role_list(self):
        """Get list of role names."""
        try:
            roles = [role.name for role in self.roles if role]
            logger.debug(f"User {self.username} roles: {roles}")
            return roles
        except Exception as e:
            logger.error(f"Error getting roles for user {self.email}: {str(e)}")
            return []
    
    @property
    def is_admin(self):
        """Check if user has admin privileges."""
        try:
            if self.is_superadmin:
                logger.debug(f"User {self.username} is superadmin")
                return True
                
            has_admin = any(
                role and hasattr(role, 'permissions') and 
                role.permissions and 'admin' in role.permissions
                for role in self.roles
            )
            logger.debug(f"User {self.username} admin check: {has_admin}")
            return has_admin
            
        except Exception as e:
            logger.error(f"Error checking admin status for user {self.email}: {str(e)}")
            return False

    @property
    def has_superadmin_role(self):
        """Check if user is superadmin."""
        try:
            return bool(self.is_superadmin)
        except Exception as e:
            logger.error(f"Error checking superadmin status: {str(e)}")
            return False

    @has_superadmin_role.setter
    def has_superadmin_role(self, value):
        """Set superadmin status."""
        self.is_superadmin = bool(value)
        if value:
            from app.models.role import Role
            superadmin_role = Role.query.filter_by(name='superadmin').first()
            if superadmin_role and superadmin_role not in self.roles:
                self.roles.append(superadmin_role)
        else:
            # Jeśli ustawiamy False, możemy usunąć rolę superadmina
            self.roles = [role for role in self.roles if role.name != 'superadmin']

    def has_role(self, role_name):
        """Check if user has specific role."""
        try:
            if self.is_superadmin:
                logger.debug(f"User {self.username} is superadmin, has all roles")
                return True
                
            has_role = any(role and role.name == role_name for role in (self.roles or []))
            logger.debug(f"User {self.username} role check for {role_name}: {has_role}")
            return has_role
            
        except Exception as e:
            logger.error(f"Error checking role {role_name} for user {self.email}: {str(e)}")
            return False

    def add_role(self, role):
        """Add role to user."""
        try:
            if role and role not in self.roles:
                self.roles.append(role)
                logger.info(f"Added role {role.name} to user {self.username}")
                db.session.commit()
        except Exception as e:
            logger.error(f"Error adding role {role.name if role else 'None'} to user {self.username}: {str(e)}")
            db.session.rollback()

    def remove_role(self, role):
        """Remove role from user."""
        try:
            if role and role in self.roles and role.name != 'superadmin':
                self.roles.remove(role)
                logger.info(f"Removed role {role.name} from user {self.username}")
                db.session.commit()
        except Exception as e:
            logger.error(f"Error removing role {role.name if role else 'None'} from user {self.username}: {str(e)}")
            db.session.rollback()

    @property
    def teams(self):
        """Get user's teams."""
        return [membership.team for membership in self.team_members]

    @property
    def team_roles(self):
        """Get user's roles in teams."""
        return {membership.team.name: membership.role for membership in self.team_members}

    def has_permission(self, permission):
        """Check if user has specific permission."""
        try:
            if self.is_superadmin:
                logger.debug(f"User {self.username} is superadmin, has all permissions")
                return True
                
            has_perm = any(
                role and hasattr(role, 'permissions') and 
                role.permissions and permission in role.permissions
                for role in (self.roles or [])
            )
            logger.debug(f"User {self.username} permission check for {permission}: {has_perm}")
            return has_perm
            
        except Exception as e:
            logger.error(f"Error checking permission {permission} for user {self.email}: {str(e)}")
            return False

    @property
    def permissions(self) -> List[str]:
        """Get all user permissions based on roles."""
        try:
            if self.is_superadmin:
                perms = list(Role.PERMISSIONS.keys())
                logger.debug(f"User {self.username} is superadmin, has all permissions: {perms}")
                return perms
            
            all_permissions = set()
            for role in (self.roles or []):
                if role and hasattr(role, 'permissions') and role.permissions:
                    all_permissions.update(role.permissions)
                    
            perms = list(all_permissions)
            logger.debug(f"User {self.username} permissions: {perms}")
            return perms
            
        except Exception as e:
            logger.error(f"Error getting permissions for user {self.email}: {str(e)}")
            return []

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        """Is anonymous."""
        return False

    def get_id(self):
        return str(self.id)

    def ensure_default_role(self):
        """Ensure user has at least the default role."""
        try:
            if not self.is_superadmin and not self.roles:
                default_role = Role.get_or_create_default_role()
                if default_role:
                    self.add_role(default_role)
                    db.session.commit()
                    logger.info(f"Added default role to user {self.username}")
        except Exception as e:
            logger.error(f"Error ensuring default role for user {self.username}: {str(e)}")
            db.session.rollback()

    @property
    def projects(self):
        """Get all projects assigned to the user."""
        try:
            from app.models import Project
            return Project.query.join(
                'assignments'
            ).filter(
                db.and_(
                    Project.assignments.any(user_id=self.id),
                    Project.status == 'active'
                )
            ).all()
        except Exception as e:
            logger.error(f"Error getting projects for user {self.username}: {str(e)}")
            return []

    @property
    def last_login(self):
        """Zwraca datę ostatniego logowania."""
        return None  # TODO: Zaimplementować po dodaniu śledzenia logowań

    def get_roles_display(self):
        """Zwraca nazwy ról jako string."""
        return ', '.join(role.name for role in self.roles)

    def get_worklog_count(self) -> Optional[int]:
        """Get the number of worklogs for this user."""
        try:
            return Worklog.query.filter_by(user_id=self.id).count()
        except Exception as e:
            logger.error(f"Error getting worklog count for user {self.email}: {str(e)}")
            return 0  # Zwróć 0 zamiast None w przypadku błędu

    def get_last_worklog(self) -> Optional[Worklog]:
        """Get the user's most recent worklog."""
        try:
            return Worklog.query.filter_by(user_id=self.id)\
                .order_by(Worklog.started.desc())\
                .first()
        except Exception as e:
            logger.error(f"Error getting last worklog for user {self.email}: {str(e)}")
            return None

    @property
    def projects(self):
        """Zwraca listę projektów użytkownika."""
        return []  # TODO: Zaimplementować po dodaniu modelu Project

    @property
    def last_login(self):
        """Zwraca datę ostatniego logowania."""
        return None  # TODO: Zaimplementować po dodaniu śledzenia logowań

    def get_roles_display(self):
        """Zwraca nazwy ról jako string."""
        return ', '.join(role.name for role in self.roles)

    def get_worklog_count(self):
        """Get number of worklogs for user."""
        try:
            # Bezpośrednie zapytanie do bazy
            return db.session.query(db.func.count(Worklog.id))\
                .filter(Worklog.user_id == self.id)\
                .scalar() or 0
        except Exception as e:
            logger.error(f"Error getting worklog count for user {self.username}: {str(e)}")
            return 0 

    @property
    def team(self):
        """Get user's current team."""
        try:
            active_membership = next((tm for tm in self.team_members if tm.is_active), None)
            return active_membership.team if active_membership else None
        except Exception as e:
            logger.error(f"Error getting team for user {self.username}: {str(e)}")
            return None 