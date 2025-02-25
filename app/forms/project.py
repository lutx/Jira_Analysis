from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, BooleanField, SelectField, SelectMultipleField
from wtforms.validators import DataRequired, Length, Optional

class ProjectForm(FlaskForm):
    """Form for project management."""
    name = StringField('Project Name', validators=[
        DataRequired(message='Project name is required'),
        Length(min=2, max=100, message='Project name must be between 2 and 100 characters')
    ])
    
    jira_key = StringField('JIRA Key', validators=[
        Optional(),
        Length(min=2, max=10, message='JIRA key must be between 2 and 10 characters')
    ])
    
    description = TextAreaField('Description', validators=[
        Optional(),
        Length(max=500, message='Description cannot be longer than 500 characters')
    ])
    
    is_active = BooleanField('Active', default=True) 