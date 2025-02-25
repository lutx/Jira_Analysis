from app.extensions import db
from datetime import datetime
import logging
from jira import JIRA
from app.exceptions import JiraValidationError, JiraConnectionError
from app.utils.crypto import encrypt_password, decrypt_password
import base64

logger = logging.getLogger(__name__)

class JiraConfig(db.Model):
    """Model for storing JIRA configuration."""
    __tablename__ = 'jira_configs'

    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(255), nullable=False)
    username = db.Column(db.String(255), nullable=False)
    password = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())
    last_sync_at = db.Column(db.DateTime, nullable=True)

    def __init__(self, **kwargs):
        """Initialize JIRA configuration."""
        try:
            # Handle password encryption before initialization
            if 'password' in kwargs:
                try:
                    kwargs['password'] = encrypt_password(kwargs['password'])
                except Exception as e:
                    logger.error(f"Failed to encrypt password: {str(e)}")
                    raise JiraValidationError("Failed to encrypt password. Please check your encryption key configuration.")

            super(JiraConfig, self).__init__(**kwargs)
        except Exception as e:
            logger.error(f"Error initializing JIRA config: {str(e)}")
            raise JiraValidationError(str(e))

    @property
    def decrypted_password(self):
        """Get decrypted password."""
        try:
            if not self.password:
                raise ValueError("No password set")
            return decrypt_password(self.password)
        except Exception as e:
            logger.error(f"Failed to decrypt password: {str(e)}")
            raise JiraValidationError("Failed to decrypt password. The configuration may need to be reset.")

    def get_basic_auth_header(self):
        """Generate Basic Auth header for JIRA API."""
        try:
            auth_string = f"{self.username}:{self.decrypted_password}"
            auth_bytes = auth_string.encode('utf-8')
            auth_b64 = base64.b64encode(auth_bytes).decode('utf-8')
            return f"Basic {auth_b64}"
        except Exception as e:
            logger.error(f"Error generating Basic Auth header: {str(e)}")
            raise JiraValidationError(str(e))

    def get_jira_client(self):
        """Get JIRA client instance."""
        try:
            decrypted_pwd = self.decrypted_password
            return JIRA(
                server=self.url,
                basic_auth=(self.username, decrypted_pwd),
                validate=True
            )
        except Exception as e:
            logger.error(f"Failed to create JIRA client: {str(e)}")
            raise JiraConnectionError(str(e))

    def validate_connection(self):
        """Validate JIRA connection with provided credentials."""
        try:
            jira = self.get_jira_client()
            jira.server_info()
            return True
        except Exception as e:
            logger.error(f"JIRA connection validation failed: {str(e)}")
            raise JiraConnectionError(str(e))

    def save(self):
        """Save JIRA configuration with validation."""
        try:
            if not self.validate_connection():
                raise JiraValidationError("Failed to validate JIRA connection")

            if self.is_active:
                JiraConfig.query.filter(JiraConfig.id != self.id).update({'is_active': False})

            db.session.add(self)
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error saving JIRA config: {str(e)}")
            raise JiraValidationError(str(e))

    @staticmethod
    def get_active_config():
        """Get the active JIRA configuration."""
        return JiraConfig.query.filter_by(is_active=True).first()

    @staticmethod
    def reset_all_configs():
        """Reset all JIRA configurations."""
        try:
            JiraConfig.query.delete()
            db.session.commit()
            logger.info("All JIRA configurations have been deleted")
            return True
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error resetting JIRA configs: {str(e)}")
            return False

    def update_sync_timestamp(self):
        """Update last sync timestamp."""
        self.last_sync_at = datetime.utcnow()
        db.session.commit()

    def to_dict(self):
        """Convert to dictionary."""
        return {
            'id': self.id,
            'url': self.url,
            'username': self.username,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'last_sync_at': self.last_sync_at.isoformat() if self.last_sync_at else None
        } 