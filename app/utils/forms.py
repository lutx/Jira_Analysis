from flask_wtf import FlaskForm
from wtforms import DateField, SelectField
from wtforms.validators import DataRequired

class ReportFilterForm(FlaskForm):
    """Formularz filtrowania raportów."""
    start_date = DateField('Data początkowa', validators=[DataRequired()])
    end_date = DateField('Data końcowa', validators=[DataRequired()])
    report_type = SelectField('Typ raportu', choices=[
        ('workload', 'Obciążenie'),
        ('activity', 'Aktywność'),
        ('efficiency', 'Efektywność')
    ]) 