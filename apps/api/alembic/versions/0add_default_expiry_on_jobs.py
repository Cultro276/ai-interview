from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0add_default_expiry_on_jobs'
down_revision = 'e653dece5464'
branch_labels = None
depends_on = None


def upgrade() -> None:
	# Add column with default 7 for existing rows
	op.add_column('jobs', sa.Column('default_invite_expiry_days', sa.Integer(), nullable=False, server_default='7'))
	# Remove server_default after data backfill to keep model-controlled default
	with op.batch_alter_table('jobs') as batch_op:
		batch_op.alter_column('default_invite_expiry_days', server_default=None)


def downgrade() -> None:
	op.drop_column('jobs', 'default_invite_expiry_days')
