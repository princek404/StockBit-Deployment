"""Add is_admin field

Revision ID: 77d6cb71b521
Revises: 
Create Date: 2025-08-15 16:50:57.554884

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = '77d6cb71b521'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    columns = [col['name'] for col in inspector.get_columns('user')]
    
    # Only add the column if it doesn't exist
    if 'is_admin' not in columns:
        with op.batch_alter_table('user', schema=None) as batch_op:
            batch_op.add_column(sa.Column('is_admin', sa.Boolean(), nullable=True, server_default='false'))
        
        # Set default value for existing users
        op.execute("UPDATE \"user\" SET is_admin = false WHERE is_admin IS NULL")
        
        # Make the column NOT NULL after setting defaults
        with op.batch_alter_table('user', schema=None) as batch_op:
            batch_op.alter_column('is_admin', existing_type=sa.Boolean(), nullable=False)

def downgrade():
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    columns = [col['name'] for col in inspector.get_columns('user')]
    
    # Only remove the column if it exists
    if 'is_admin' in columns:
        with op.batch_alter_table('user', schema=None) as batch_op:
            batch_op.drop_column('is_admin')
    ${downgrades if downgrades else "pass"}
