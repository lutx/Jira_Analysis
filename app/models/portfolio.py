from app.extensions import db
from datetime import datetime
from sqlalchemy import text
import logging

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
    """Portfolio model."""
    __tablename__ = 'portfolios'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    created_by = db.Column(db.String(255), nullable=True)  # Added to match schema.sql

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
        """Convert portfolio to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'projects_count': len(self.projects) if self.projects else 0,
            'is_active': self.is_active,
            'created_by': self.created_by
        }

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