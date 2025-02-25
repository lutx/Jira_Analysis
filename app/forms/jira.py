from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField
from wtforms.validators import DataRequired, URL

class JiraSettingsForm(FlaskForm):
    url = StringField('URL Jira', validators=[DataRequired(), URL()])
    username = StringField('Nazwa użytkownika', validators=[DataRequired()])
    api_token = PasswordField('Token API', validators=[DataRequired()])
    project_keys = StringField('Klucze projektów (oddzielone przecinkami)') 