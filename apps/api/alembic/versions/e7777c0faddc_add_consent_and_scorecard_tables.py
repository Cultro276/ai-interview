"""add consent and scorecard tables

Revision ID: e7777c0faddc
Revises: f1a2b3c4d5e6
Create Date: 2025-08-22 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e7777c0faddc'
down_revision = 'f1a2b3c4d5e6'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'candidate_consents',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('candidate_id', sa.Integer(), sa.ForeignKey('candidates.id', ondelete='CASCADE'), nullable=False),
        sa.Column('interview_id', sa.Integer(), sa.ForeignKey('interviews.id', ondelete='CASCADE'), nullable=False),
        sa.Column('accepted_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('ip', sa.String(length=64), nullable=True),
        sa.Column('text_version', sa.String(length=32), nullable=True),
    )

    op.create_table(
        'interview_scorecards',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('interview_id', sa.Integer(), sa.ForeignKey('interviews.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('evaluator_user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('competency_scores', sa.JSON(), nullable=False),
        sa.Column('overall', sa.Float(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade():
    op.drop_table('interview_scorecards')
    op.drop_table('candidate_consents')


