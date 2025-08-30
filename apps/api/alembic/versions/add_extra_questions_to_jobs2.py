"""add extra_questions to jobs

Revision ID: add_extra_questions_jobs2
Revises: add_phone_linkedin2
Create Date: 2025-08-30 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_extra_questions_jobs2'
down_revision = 'add_phone_linkedin2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('jobs') as batch_op:
        try:
            batch_op.add_column(sa.Column('extra_questions', sa.Text(), nullable=True))
        except Exception:
            # Column may already exist
            pass


def downgrade() -> None:
    with op.batch_alter_table('jobs') as batch_op:
        try:
            batch_op.drop_column('extra_questions')
        except Exception:
            pass


