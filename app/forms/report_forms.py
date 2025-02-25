from flask_wtf import FlaskForm
from wtforms import DateField, SelectField, SubmitField
from datetime import datetime, timedelta

class ReportFilterForm(FlaskForm):
    start_date = DateField('Data początkowa', 
                          default=lambda: datetime.now() - timedelta(days=30))
    end_date = DateField('Data końcowa', 
                        default=lambda: datetime.now())
    submit = SubmitField('Generuj raport')

class RoleDistributionForm(ReportFilterForm):
    portfolio = SelectField('Portfolio', choices=[], coerce=int)

class ShadowWorkForm(ReportFilterForm):
    pass

class AvailabilityForm(ReportFilterForm):
    team = SelectField('Zespół', choices=[], coerce=int) 