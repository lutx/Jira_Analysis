from app.extensions import db
from datetime import datetime
import logging
import json

logger = logging.getLogger(__name__)

class Role(db.Model):
    """Model for user roles."""
    __tablename__ = 'roles'
    __table_args__ = {'extend_existing': True}
    
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
        'manage_reports': 'Report management'
    }
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    description = db.Column(db.String(255))
    permissions = db.Column(db.String(1000))  # Change to String to store JSON as text
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
        """Initialize role with permissions."""
        try:
            super().__init__(**kwargs)
            
            # Initialize permissions
            if 'permissions' in kwargs:
                if isinstance(kwargs['permissions'], (list, tuple)):
                    perms = [p for p in kwargs['permissions'] if p in self.PERMISSIONS]
                    self.set_permissions(perms)
                    logger.info(f"Initialized role {kwargs.get('name')} with permissions: {perms}")
                else:
                    logger.warning(f"Invalid permissions format for role {kwargs.get('name')}: {kwargs['permissions']}")
                    self.set_permissions([])
            else:
                logger.info(f"No permissions provided for role {kwargs.get('name')}, using empty list")
                self.set_permissions([])
                
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
        """Convert role to dictionary."""
        try:
            return {
                'id': self.id,
                'name': self.name,
                'description': self.description,
                'permissions': self.get_permissions(),
                'created_at': self.created_at.isoformat() if self.created_at else None,
                'updated_at': self.updated_at.isoformat() if self.updated_at else None
            }
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