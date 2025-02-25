from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, EmailField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError, Optional
from app.models import User
import logging

logger = logging.getLogger(__name__)

class LoginForm(FlaskForm):
    """Formularz logowania."""
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Login')

    def validate(self):
        logger.info("Validating login form")
        if not super().validate():
            logger.error(f"Form validation failed: {self.errors}")
            return False
            
        logger.info(f"Form data: {self.data}")
        return True

    def validate_username(self, field):
        logger.debug(f"Validating username: {field.data}")
        user = User.query.filter_by(username=field.data).first()
        if not user:
            logger.warning(f"User not found: {field.data}")
            raise ValidationError('Nieprawidłowa nazwa użytkownika lub hasło.')
        logger.debug(f"Username validation passed for: {field.data}")

    def validate_password(self, field):
        logger.debug("Validating password")
        user = User.query.filter_by(username=self.username.data).first()
        if user and not user.check_password(field.data):
            logger.warning(f"Invalid password for user: {self.username.data}")
            raise ValidationError('Nieprawidłowa nazwa użytkownika lub hasło.')
        logger.debug("Password validation passed")

class RegistrationForm(FlaskForm):
    username = StringField('Nazwa użytkownika', validators=[
        DataRequired(),
        Length(min=3, max=64)
    ])
    email = EmailField('Email', validators=[
        DataRequired(),
        Email(),
        Length(max=120)
    ])
    password = PasswordField('Hasło', validators=[
        DataRequired(),
        Length(min=6, message='Hasło musi mieć co najmniej 6 znaków')
    ])
    password2 = PasswordField('Powtórz hasło', validators=[
        DataRequired(),
        EqualTo('password', message='Hasła muszą być identyczne')
    ])
    submit = SubmitField('Zarejestruj')

    def validate_username(self, field):
        user = User.query.filter_by(username=field.data).first()
        if user:
            raise ValidationError('Ta nazwa użytkownika jest już zajęta.')

    def validate_email(self, field):
        user = User.query.filter_by(email=field.data).first()
        if user:
            raise ValidationError('Ten adres email jest już używany.')

class UserSettingsForm(FlaskForm):
    """Form for user settings."""
    email = StringField('Email', validators=[DataRequired(), Email()])
    display_name = StringField('Nazwa wyświetlana')
    jira_username = StringField('Nazwa użytkownika JIRA')
    jira_email = StringField('Email JIRA', validators=[Optional(), Email()])
    password = PasswordField('Nowe hasło', validators=[
        Optional(),
        Length(min=8, message='Hasło musi mieć co najmniej 8 znaków')
    ])
    password_confirm = PasswordField('Potwierdź hasło', validators=[
        Optional(),
        EqualTo('password', message='Hasła muszą być identyczne')
    ])
    submit = SubmitField('Zapisz zmiany') 