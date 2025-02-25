from app.models.user import User
from app.models.role import Role
from app.extensions import db
from flask import current_app
import logging

logger = logging.getLogger(__name__)

def check_user_roles():
    """Check and fix user roles."""
    try:
        # Get superadmin email from config
        email = current_app.config.get('SUPERADMIN_EMAIL')
        if not email:
            logger.error("SUPERADMIN_EMAIL not set")
            return
            
        # Get or create roles
        admin_role = Role.query.filter_by(name='admin').first()
        if not admin_role:
            admin_role = Role(name='admin', description='Administrator')
            db.session.add(admin_role)
            db.session.commit()
            logger.info("Created admin role")
            
        superadmin_role = Role.query.filter_by(name='superadmin').first()
        if not superadmin_role:
            superadmin_role = Role(name='superadmin', description='Super Administrator')
            db.session.add(superadmin_role)
            db.session.commit()
            logger.info("Created superadmin role")
            
        # Get user
        user = User.query.filter_by(email=email).first()
        if not user:
            logger.error(f"User not found: {email}")
            return
            
        # Ensure user has both roles
        if admin_role not in user.role_objects:
            user.role_objects.append(admin_role)
            logger.info(f"Added admin role to user {email}")
            
        if superadmin_role not in user.role_objects:
            user.role_objects.append(superadmin_role)
            logger.info(f"Added superadmin role to user {email}")
            
        db.session.commit()
        logger.info(f"User roles updated: {user.roles}")
        
    except Exception as e:
        logger.error(f"Error checking roles: {str(e)}")
        db.session.rollback() 