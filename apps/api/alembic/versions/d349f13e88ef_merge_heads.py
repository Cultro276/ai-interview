"""merge heads

Revision ID: d349f13e88ef
Revises: 0add_default_expiry_on_jobs, 779d02bbe3af
Create Date: 2025-08-18 12:36:15.551505

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd349f13e88ef'
down_revision = ('0add_default_expiry_on_jobs', '779d02bbe3af')
branch_labels = None
depends_on = None

def upgrade():
    pass


def downgrade():
    pass 