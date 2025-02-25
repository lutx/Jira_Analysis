from flask_wtf import FlaskForm
from wtforms import StringField, BooleanField
from wtforms.validators import DataRequired, URL

class JiraConfigForm(FlaskForm):
    jira_url = StringField('JIRA URL', validators=[
        DataRequired(),
        URL(message='Please enter a valid URL')
    ])
    jira_username = StringField('JIRA Username', validators=[DataRequired()])
    jira_api_token = StringField('JIRA API Token', validators=[DataRequired()])
    is_enabled = BooleanField('Enable JIRA Integration') 