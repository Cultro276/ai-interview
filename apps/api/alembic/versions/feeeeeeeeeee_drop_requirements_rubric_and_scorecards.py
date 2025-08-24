"""drop requirements/rubric columns and interview_scorecards table

Revision ID: feeeeeeeeeee
Revises: e8888c0feed
Create Date: 2025-08-22 12:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'feeeeeeeeeee'
down_revision = 'e8888c0feed'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop manual configuration columns from jobs
    with op.batch_alter_table('jobs') as batch_op:
        try:
            batch_op.drop_column('requirements_config')
        except Exception:
            pass
        try:
            batch_op.drop_column('rubric_weights')
        except Exception:
            pass

    # Drop scorecards table if present
    try:
        op.drop_table('interview_scorecards')
    except Exception:
        # Table may not exist if earlier revision wasn't applied
        pass


def downgrade() -> None:
    # Recreate scorecards table
    op.create_table(
        'interview_scorecards',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('interview_id', sa.Integer(), sa.ForeignKey('interviews.id', ondelete='CASCADE'), nullable=False),
        sa.Column('evaluator_user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('competency_scores', sa.JSON(), nullable=False),
        sa.Column('overall', sa.Float(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Re-add configuration columns to jobs
    with op.batch_alter_table('jobs') as batch_op:
        batch_op.add_column(sa.Column('requirements_config', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('rubric_weights', sa.JSON(), nullable=True))


