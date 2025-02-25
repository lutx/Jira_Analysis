from app.extensions import db
from datetime import datetime

# Tabela asocjacyjna dla relacji many-to-many między Portfolio a Project
portfolio_projects = db.Table(
    'portfolio_projects',
    db.Column('portfolio_id', db.Integer, db.ForeignKey('portfolios.id'), primary_key=True),
    db.Column('project_id', db.Integer, db.ForeignKey('projects.id'), primary_key=True),
    extend_existing=True
)

# Możemy usunąć klasę PortfolioProject, ponieważ używamy tabeli asocjacyjnej 