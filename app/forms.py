from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, BooleanField, SubmitField, EmailField
from wtforms.validators import DataRequired, Email, Length, ValidationError, Optional
from email_validator import validate_email, EmailNotValidError

class LoginForm(FlaskForm):
    """Form for user login."""
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Login')

class UserForm(FlaskForm):
    """Form for user management."""
    username = StringField('Username', validators=[
        DataRequired(message='Username is required'),
        Length(min=3, max=50, message='Username must be between 3 and 50 characters')
    ])
    email = StringField('Email', validators=[
        DataRequired(message='Email is required'),
        Email(message='Invalid email address')
    ])
    password = PasswordField('Password', validators=[
        Length(min=6, message='Password must be at least 6 characters long')
    ])

    def validate_email(self, field):
        try:
            validate_email(field.data)
        except EmailNotValidError as e:
            raise ValidationError(str(e))

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