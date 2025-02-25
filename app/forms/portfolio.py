from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectMultipleField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length

class PortfolioForm(FlaskForm):
    """Portfolio management form."""
    class Meta:
        csrf = True  # Enable CSRF protection for this form
        csrf_field_name = "csrf_token"  # Use standard field name
    
    name = StringField('Nazwa', validators=[
        DataRequired(message='Nazwa jest wymagana'),
        Length(min=3, max=100, message='Nazwa musi mieć od 3 do 100 znaków')
    ])
    description = TextAreaField('Opis', validators=[
        Length(max=500, message='Opis nie może być dłuższy niż 500 znaków')
    ])
    projects = SelectMultipleField('Projekty', coerce=int)
    is_active = BooleanField('Aktywne', default=True)
    submit = SubmitField('Zapisz')

    def __init__(self, *args, **kwargs):
        super(PortfolioForm, self).__init__(*args, **kwargs)
        from app.models.project import Project
        self.projects.choices = [
            (project.id, project.name) 
            for project in Project.query.order_by(Project.name).all()
        ] 