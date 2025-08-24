"""merge current heads

Revision ID: 98999511af16
Revises: e11111111111, feeeeeeeeeee
Create Date: 2025-08-22 21:19:09.764861

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '98999511af16'
down_revision = ('e11111111111', 'feeeeeeeeeee')
branch_labels = None
depends_on = None

def upgrade():
    pass


def downgrade():
    pass 