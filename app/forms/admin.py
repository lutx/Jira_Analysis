from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectMultipleField, TextAreaField, BooleanField, SelectField, IntegerField, EmailField, SubmitField
from wtforms.validators import DataRequired, Email, Length, URL, NumberRange, Optional, ValidationError
from app.models.jira_config import JiraConfig

class UserForm(FlaskForm):
    username = StringField('Nazwa użytkownika', validators=[DataRequired(), Length(min=3, max=64)])
    email = EmailField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Hasło', validators=[DataRequired(), Length(min=6)])
    display_name = StringField('Wyświetlana nazwa', validators=[Optional(), Length(max=64)])
    is_active = BooleanField('Aktywny', default=True)
    roles = SelectMultipleField('Role', coerce=int)

class RoleForm(FlaskForm):
    """Formularz zarządzania rolami."""
    name = StringField('Nazwa', validators=[
        DataRequired(message='Nazwa jest wymagana'),
        Length(min=3, max=64, message='Nazwa musi mieć od 3 do 64 znaków')
    ])
    description = TextAreaField('Opis', validators=[
        Optional(),
        Length(max=255, message='Opis nie może być dłuższy niż 255 znaków')
    ])
    permissions = SelectMultipleField('Uprawnienia', 
                                    choices=[], 
                                    coerce=str,
                                    validators=[DataRequired(message='Wybierz co najmniej jedno uprawnienie')])

    def __init__(self, *args, **kwargs):
        super(RoleForm, self).__init__(*args, **kwargs)
        from app.models.role import Role
        self.permissions.choices = [(k, v) for k, v in Role.get_available_permissions().items()]

class JiraSettingsForm(FlaskForm):
    """Form for JIRA configuration settings."""
    url = StringField('JIRA URL', validators=[
        DataRequired(message='JIRA URL is required'),
        URL(message='Please enter a valid URL')
    ])
    username = StringField('Username', validators=[
        DataRequired(message='Username is required')
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message='Password is required')
    ])
    is_active = BooleanField('Active', default=True)

    def validate_url(self, field):
        if not field.data.startswith(('http://', 'https://')):
            raise ValidationError('URL must start with http:// or https://')

    def validate_password(self, field):
        if not self.password.data and not self.password.flags.optional:
            raise ValidationError('Password is required')

class SystemSettingsForm(FlaskForm):
    system_name = StringField('Nazwa systemu', validators=[DataRequired()])
    admin_email = StringField('Email administratora', validators=[
        DataRequired(),
        Email()
    ])
    submit = SubmitField('Zapisz')

class SettingsForm(FlaskForm):
    """Formularz ustawień systemu."""
    sync_interval = IntegerField(
        'Interwał synchronizacji (sekundy)', 
        validators=[
            DataRequired(),
            NumberRange(min=60, max=86400)
        ],
        default=3600
    )
    
    log_level = SelectField(
        'Poziom logowania',
        choices=[
            ('10', 'DEBUG'),
            ('20', 'INFO'),
            ('30', 'WARNING'),
            ('40', 'ERROR'),
            ('50', 'CRITICAL')
        ],
        default='20'
    )
    
    cache_timeout = IntegerField(
        'Czas życia cache (sekundy)',
        validators=[
            DataRequired(),
            NumberRange(min=60, max=3600)
        ],
        default=300
    )

class JiraConfigForm(FlaskForm):
    """Formularz konfiguracji JIRA."""
    url = StringField('URL Jiry', 
                     validators=[DataRequired(), URL()],
                     render_kw={"placeholder": "https://jira-test.lbpro.pl"})
    username = StringField('Email użytkownika', 
                         validators=[DataRequired(), Email()],
                         render_kw={"placeholder": "your-email@lbpro.pl"})
    password = PasswordField('Hasło',
                           validators=[DataRequired()],
                           render_kw={"placeholder": "Wprowadź hasło"})
    submit = SubmitField('Zapisz konfigurację')

class ProjectForm(FlaskForm):
    """Formularz projektu."""
    name = StringField('Nazwa', validators=[DataRequired()])
    jira_key = StringField('Klucz JIRA', validators=[DataRequired()])
    description = TextAreaField('Opis')
    is_active = BooleanField('Aktywny', default=True)
    submit = SubmitField('Zapisz') 