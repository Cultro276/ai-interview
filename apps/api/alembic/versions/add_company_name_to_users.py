"""add_company_name_to_users

Revision ID: company_001
Revises: add_unique_assistant_msg_idx, aud_0001
Create Date: 2025-01-27 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'company_001'
down_revision = ('add_unique_assistant_msg_idx', 'aud_0001')  # Merge both heads
branch_labels = None
depends_on = None

def upgrade():
    # Add company_name column to users table
    op.add_column('users', sa.Column('company_name', sa.String(255), nullable=True))

def downgrade():
    # Remove company_name column from users table
    op.drop_column('users', 'company_name')
