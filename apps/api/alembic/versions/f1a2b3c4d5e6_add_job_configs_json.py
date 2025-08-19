"""Add requirements_config and rubric_weights to jobs

Revision ID: f1a2b3c4d5e6
Revises: 9eb5d46944a1
Create Date: 2025-08-19 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f1a2b3c4d5e6'
down_revision = '9eb5d46944a1'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('jobs') as batch_op:
        batch_op.add_column(sa.Column('requirements_config', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('rubric_weights', sa.JSON(), nullable=True))


def downgrade():
    with op.batch_alter_table('jobs') as batch_op:
        batch_op.drop_column('rubric_weights')
        batch_op.drop_column('requirements_config')


