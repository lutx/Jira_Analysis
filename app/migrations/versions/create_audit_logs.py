"""Create audit logs table

Revision ID: create_audit_logs
Revises: 
Create Date: 2024-02-20 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'create_audit_logs'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('action', sa.String(length=255), nullable=False),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

def downgrade():
    op.drop_table('audit_logs') 