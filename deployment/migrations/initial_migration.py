"""Initial migration for Supabase

Revision ID: 9a8b7c6d5e4f3a2b1c0d
Revises: 
Create Date: 2023-10-15 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '9a8b7c6d5e4f3a2b1c0d'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Create users table with is_admin column
    op.create_table('user',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=80), nullable=False),
        sa.Column('email', sa.String(length=120), nullable=False),
        sa.Column('password', sa.String(length=120), nullable=False),
        sa.Column('business_name', sa.String(length=100), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('is_premium', sa.Boolean(), nullable=True),
        sa.Column('premium_since', sa.DateTime(), nullable=True),
        sa.Column('phone', sa.String(length=20), nullable=True),
        sa.Column('subscription_active', sa.Boolean(), nullable=True),
        sa.Column('is_admin', sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('username')
    )
    
    # Create other tables...
    op.create_table('product',
        # ... columns ...
    )
    # Add other tables similarly

def downgrade():
    op.drop_table('payment_verification')
    op.drop_table('sale')
    op.drop_table('supplier')
    op.drop_table('product')
    op.drop_table('user')
