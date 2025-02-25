from app.extensions import db
from datetime import datetime

class PortfolioAssignment(db.Model):
    __tablename__ = 'portfolio_assignments'
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.Integer, primary_key=True)
    portfolio_id = db.Column(db.Integer, db.ForeignKey('portfolios.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    role = db.Column(db.String(50), nullable=False)  # e.g., 'manager', 'member'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    portfolio = db.relationship('Portfolio', back_populates='assignments')
    user = db.relationship('User', back_populates='portfolio_assignments')

    def __repr__(self):
        return f'<PortfolioAssignment {self.user_id}-{self.portfolio_id}>' 