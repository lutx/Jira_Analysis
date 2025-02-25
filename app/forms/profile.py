from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, EmailField
from wtforms.validators import DataRequired, Email, Length, Optional

class ProfileForm(FlaskForm):
    display_name = StringField('Display Name', validators=[DataRequired(), Length(min=3, max=120)])
    email = EmailField('Email', validators=[DataRequired(), Email()])
    current_password = PasswordField('Current Password', validators=[Optional()])
    new_password = PasswordField('New Password', validators=[Optional(), Length(min=6)]) 