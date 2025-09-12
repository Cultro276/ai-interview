"""add job.rubric_json

Revision ID: aabbccddeeff_add_job_rubric_json
Revises: e11111111111_merge_all_heads
Create Date: 2025-09-12 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'aabbccddeeff_add_job_rubric_json'
# Allow this migration to apply on top of latest known heads if merge file is missing
down_revision: Union[str, None] = 'e11111111111'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('jobs') as batch_op:
        batch_op.add_column(sa.Column('rubric_json', sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('jobs') as batch_op:
        batch_op.drop_column('rubric_json')


