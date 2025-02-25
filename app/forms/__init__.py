# Pusty plik __init__.py aby utworzyć pakiet 
from app.forms.auth import LoginForm
from app.forms.admin import SettingsForm, JiraSettingsForm, SystemSettingsForm, UserForm, RoleForm
from app.forms.team import TeamForm
from app.forms.portfolio import PortfolioForm
from app.forms.project import ProjectForm
from app.forms.assignment import ProjectAssignmentForm
from app.forms.leave import LeaveForm
from app.forms.profile import ProfileForm
from app.forms.settings import GeneralSettingsForm
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, EmailField
from wtforms.validators import DataRequired, Email, Length, ValidationError, Optional, EqualTo
from app.models import User

class UserSettingsForm(FlaskForm):
    """Formularz ustawień użytkownika."""
    display_name = StringField('Wyświetlana nazwa', validators=[
        Optional(),
        Length(min=2, max=64)
    ])
    email = EmailField('Email', validators=[
        DataRequired(),
        Email(),
        Length(max=120)
    ])
    submit = SubmitField('Zapisz zmiany')

    def __init__(self, *args, **kwargs):
        super(UserSettingsForm, self).__init__(*args, **kwargs)

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Login')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email()])  # Używamy wbudowanej walidacji Email
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField('Repeat Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

    def validate_username(self, field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError('Username already in use.')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('Email already registered.')

__all__ = [
    'LoginForm',
    'UserForm',
    'UserSettingsForm',
    'RoleForm',
    'TeamForm',
    'PortfolioForm',
    'ProjectForm',
    'ProjectAssignmentForm',
    'LeaveForm',
    'ProfileForm',
    'GeneralSettingsForm',
    'SettingsForm',
    'JiraSettingsForm',
    'SystemSettingsForm'
] 