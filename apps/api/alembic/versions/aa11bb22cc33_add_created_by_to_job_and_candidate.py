"""
add created_by_user_id to jobs and candidates

Revision ID: aa11bb22cc33
Revises: e11111111111_merge_all_heads
Create Date: 2025-09-10
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'aa11bb22cc33'
down_revision = 'e11111111111'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('jobs', sa.Column('created_by_user_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_jobs_created_by_user', 'jobs', 'users', ['created_by_user_id'], ['id'], ondelete='SET NULL')

    op.add_column('candidates', sa.Column('created_by_user_id', sa.Integer(), nullable=True))
    # Candidate creator can be any user in tenant; not strictly FK to avoid circular tenant constrains


def downgrade() -> None:
    op.drop_column('candidates', 'created_by_user_id')
    try:
        op.drop_constraint('fk_jobs_created_by_user', 'jobs', type_='foreignkey')
    except Exception:
        pass
    op.drop_column('jobs', 'created_by_user_id')


