from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectMultipleField, validators
from app.models.role import Role

class RoleForm(FlaskForm):
    """Form for creating and editing roles."""
    name = StringField('Name', [
        validators.DataRequired(),
        validators.Length(min=2, max=80)
    ])
    description = TextAreaField('Description', [
        validators.Optional(),
        validators.Length(max=255)
    ])
    permissions = SelectMultipleField('Permissions', 
        choices=[(k, v) for k, v in Role.PERMISSIONS.items()],
        validators=[validators.DataRequired()]
    )

    def validate_name(self, field):
        """Validate that the role name is unique."""
        if self.original_name != field.data:
            existing = Role.query.filter_by(name=field.data).first()
            if existing:
                raise validators.ValidationError('Role name already exists.') 