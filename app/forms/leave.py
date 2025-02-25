from flask_wtf import FlaskForm
from wtforms import DateField, SelectField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, ValidationError
from datetime import date

class LeaveForm(FlaskForm):
    start_date = DateField('Data rozpoczęcia', validators=[DataRequired()])
    end_date = DateField('Data zakończenia', validators=[DataRequired()])
    leave_type = SelectField('Typ urlopu', choices=[
        ('vacation', 'Urlop wypoczynkowy'),
        ('sick', 'Urlop chorobowy'),
        ('other', 'Inny')
    ])
    description = TextAreaField('Opis')
    submit = SubmitField('Złóż wniosek')

    def validate_start_date(self, field):
        if field.data < date.today():
            raise ValidationError('Data rozpoczęcia nie może być w przeszłości')

    def validate_end_date(self, field):
        if field.data < self.start_date.data:
            raise ValidationError('Data zakończenia nie może być wcześniejsza niż data rozpoczęcia') 