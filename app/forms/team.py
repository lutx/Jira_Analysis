from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectMultipleField, SelectField
from wtforms.validators import DataRequired, Length
from app.extensions import db
import logging
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)

class TeamForm(FlaskForm):
    """Form for team management."""
    name = StringField('Team Name', validators=[
        DataRequired(message='Team name is required'),
        Length(min=2, max=100, message='Team name must be between 2 and 100 characters')
    ])
    description = TextAreaField('Description', validators=[
        Length(max=500, message='Description cannot be longer than 500 characters')
    ])
    leader_id = SelectField('Leader', coerce=int)
    portfolio_id = SelectField('Portfolio', coerce=int)
    members = SelectMultipleField('Members', coerce=int)

    def __init__(self, *args, **kwargs):
        """Initialize the form with dynamic choices for select fields."""
        super().__init__(*args, **kwargs)
        
        # Set default choices
        self.leader_id.choices = [(0, '-- Select Leader --')]
        self.portfolio_id.choices = [(0, '-- Select Portfolio --')]
        self.members.choices = []
        
        try:
            from app.models import User, Portfolio
            
            # Get all active users for leader selection
            try:
                users = User.query.filter_by(is_active=True).all()
                if users:
                    logger.info(f"Found {len(users)} active users for leader selection")
                    self.leader_id.choices = [(0, '-- Select Leader --')] + [
                        (u.id, u.display_name or u.username) for u in users
                    ]
                    # Set member choices from active users
                    self.members.choices = [
                        (u.id, u.display_name or u.username) for u in users
                    ]
                else:
                    logger.warning("No active users found for leader selection")
            except SQLAlchemyError as e:
                logger.error(f"Database error querying users: {str(e)}")
            
            # Get all portfolios
            try:
                portfolios = Portfolio.query.all()
                if portfolios:
                    logger.info(f"Found {len(portfolios)} portfolios")
                    self.portfolio_id.choices = [(0, '-- Select Portfolio --')] + [
                        (p.id, p.name) for p in portfolios
                    ]
                else:
                    logger.warning("No portfolios found")
            except SQLAlchemyError as e:
                logger.error(f"Database error querying portfolios: {str(e)}")
            
        except Exception as e:
            logger.error(f"Error initializing TeamForm: {str(e)}", exc_info=True)
            
    def validate_leader_id(self, field):
        """Validate leader selection."""
        if field.data != 0 and field.data not in [choice[0] for choice in self.leader_id.choices]:
            raise ValueError('Invalid leader selected')
            
    def validate_portfolio_id(self, field):
        """Validate portfolio selection."""
        if field.data != 0 and field.data not in [choice[0] for choice in self.portfolio_id.choices]:
            raise ValueError('Invalid portfolio selected')
            
    def validate_members(self, field):
        """Validate member selection."""
        valid_ids = [choice[0] for choice in self.members.choices]
        invalid_members = [m for m in field.data if m not in valid_ids]
        if invalid_members:
            raise ValueError(f'Invalid member IDs: {", ".join(map(str, invalid_members))}') 