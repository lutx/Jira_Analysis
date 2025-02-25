from app.extensions import db
from datetime import datetime

class TokenBlocklist(db.Model):
    __tablename__ = 'token_blocklist'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(36), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    revoked_by_id = db.Column(db.Integer, db.ForeignKey('users.id')) 