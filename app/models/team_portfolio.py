from app.extensions import db
from datetime import datetime

# Tabela asocjacyjna dla relacji team-portfolio
team_portfolios = db.Table('team_portfolios',
    db.Column('team_id', db.Integer, db.ForeignKey('teams.id'), primary_key=True),
    db.Column('portfolio_id', db.Integer, db.ForeignKey('portfolios.id'), primary_key=True),
    db.Column('created_at', db.DateTime, default=datetime.utcnow),
    extend_existing=True
) 