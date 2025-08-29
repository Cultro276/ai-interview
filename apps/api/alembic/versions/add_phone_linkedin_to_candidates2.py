"""add phone/linkedin_url to candidates (chain from current head)

Revision ID: add_phone_linkedin2
Revises: aabbccddeeff
Create Date: 2025-08-29 00:10:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_phone_linkedin2'
down_revision = 'aabbccddeeff'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('candidates') as batch_op:
        try:
            batch_op.add_column(sa.Column('phone', sa.String(length=50), nullable=True))
        except Exception:
            pass
        try:
            batch_op.add_column(sa.Column('linkedin_url', sa.String(length=255), nullable=True))
        except Exception:
            pass


def downgrade() -> None:
    with op.batch_alter_table('candidates') as batch_op:
        try:
            batch_op.drop_column('linkedin_url')
        except Exception:
            pass
        try:
            batch_op.drop_column('phone')
        except Exception:
            pass


