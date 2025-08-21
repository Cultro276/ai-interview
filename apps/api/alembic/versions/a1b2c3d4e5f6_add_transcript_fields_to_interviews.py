"""Add transcript fields to interviews

Revision ID: a1b2c3d4e5f6
Revises: 9eb5d46944a1
Create Date: 2025-08-21 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '9eb5d46944a1'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('interviews') as batch_op:
        batch_op.add_column(sa.Column('transcript_text', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('transcript_provider', sa.String(length=50), nullable=True))


def downgrade():
    with op.batch_alter_table('interviews') as batch_op:
        batch_op.drop_column('transcript_provider')
        batch_op.drop_column('transcript_text')


