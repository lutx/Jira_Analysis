from app.extensions import db
from datetime import datetime

class Setting(db.Model):
    """Model reprezentujący ustawienia aplikacji."""
    __tablename__ = 'settings'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), unique=True, nullable=False)
    value = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @classmethod
    def get_value(cls, name, default=None):
        """Get setting value by name."""
        setting = cls.query.filter_by(name=name).first()
        return setting.value if setting else default

    @classmethod
    def set_value(cls, name, value):
        """Set setting value."""
        setting = cls.query.filter_by(name=name).first()
        if setting:
            setting.value = value
        else:
            setting = cls(name=name, value=value)
            db.session.add(setting)
        db.session.commit()

    def __repr__(self):
        return f'<Setting {self.name}={self.value}>' 