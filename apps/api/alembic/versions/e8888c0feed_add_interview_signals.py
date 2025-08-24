"""add interview_signals table

Revision ID: e8888c0feed
Revises: e7777c0faddc
Create Date: 2025-08-22 00:10:00.000000

"""

from alembic import op
import sqlalchemy as sa


revision = 'e8888c0feed'
down_revision = 'e7777c0faddc'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'interview_signals',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('interview_id', sa.Integer(), sa.ForeignKey('interviews.id', ondelete='CASCADE'), nullable=False),
        sa.Column('kind', sa.String(length=50), nullable=False),
        sa.Column('meta', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade():
    op.drop_table('interview_signals')


