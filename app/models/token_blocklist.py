from app.extensions import db
from datetime import datetime

class TokenBlocklist(db.Model):
    """Model for storing revoked tokens."""
    __tablename__ = 'token_blocklist'
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(36), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    revoked_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    revoked_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Relacje
    user = db.relationship(
        'User',
        foreign_keys=[user_id],
        back_populates='tokens_blocklist'
    )
    
    revoked_by = db.relationship(
        'User',
        foreign_keys=[revoked_by_id],
        back_populates='revoked_tokens'
    )

    def __repr__(self):
        return f'<TokenBlocklist {self.jti}>'

    def to_dict(self):
        return {
            'id': self.id,
            'jti': self.jti,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'revoked_at': self.revoked_at.isoformat() if self.revoked_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'user_id': self.user_id,
            'revoked_by_id': self.revoked_by_id
        }

    @classmethod
    def add_to_blocklist(cls, jti: str, user_id: int, expires: datetime, revoked_by: int = None):
        """Dodaje token do czarnej listy."""
        token = cls(
            jti=jti,
            user_id=user_id,
            expires_at=expires,
            revoked_by_id=revoked_by
        )
        db.session.add(token)
        db.session.commit()
        return token

    @classmethod
    def is_blocklisted(cls, jti: str) -> bool:
        """Sprawdza czy token jest na czarnej liście."""
        return cls.query.filter_by(jti=jti).first() is not None 