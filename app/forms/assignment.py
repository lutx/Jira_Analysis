from flask_wtf import FlaskForm
from wtforms import SelectField, FloatField, DateField
from wtforms.validators import DataRequired, NumberRange

class ProjectAssignmentForm(FlaskForm):
    user_id = SelectField('Użytkownik', coerce=int, validators=[DataRequired()])
    role_id = SelectField('Rola', coerce=int, validators=[DataRequired()])
    planned_hours = FloatField('Planowane godziny', validators=[
        DataRequired(),
        NumberRange(min=0, max=999)
    ])
    start_date = DateField('Data rozpoczęcia', validators=[DataRequired()])
    end_date = DateField('Data zakończenia') 