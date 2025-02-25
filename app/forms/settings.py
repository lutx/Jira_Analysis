from flask_wtf import FlaskForm
from wtforms import SelectField
from wtforms.validators import DataRequired

class GeneralSettingsForm(FlaskForm):
    language = SelectField('Language', choices=[
        ('en', 'English'),
        ('pl', 'Polski')
    ], validators=[DataRequired()])
    
    timezone = SelectField('Time Zone', choices=[
        ('UTC', 'UTC'),
        ('Europe/Warsaw', 'Europe/Warsaw')
    ], validators=[DataRequired()])
    
    date_format = SelectField('Date Format', choices=[
        ('YYYY-MM-DD', 'YYYY-MM-DD'),
        ('DD-MM-YYYY', 'DD-MM-YYYY'),
        ('MM/DD/YYYY', 'MM/DD/YYYY')
    ], validators=[DataRequired()]) 