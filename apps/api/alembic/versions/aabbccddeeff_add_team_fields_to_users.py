"""add team/tenant fields to users

Revision ID: aabbccddeeff
Revises: e8888c0feed_add_interview_signals
Create Date: 2025-08-26 00:00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "aabbccddeeff"
# Set the down_revision to the latest applied head so this migration runs next
down_revision = "9b7d898addda"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("owner_user_id", sa.Integer(), nullable=True))
    op.add_column("users", sa.Column("role", sa.String(length=50), nullable=True))
    op.add_column("users", sa.Column("can_manage_jobs", sa.Boolean(), server_default=sa.text("false"), nullable=False))
    op.add_column("users", sa.Column("can_manage_candidates", sa.Boolean(), server_default=sa.text("false"), nullable=False))
    op.add_column("users", sa.Column("can_view_interviews", sa.Boolean(), server_default=sa.text("false"), nullable=False))
    op.add_column("users", sa.Column("can_manage_members", sa.Boolean(), server_default=sa.text("false"), nullable=False))
    try:
        op.create_foreign_key(
            "fk_users_owner_user_id_users",
            "users",
            "users",
            ["owner_user_id"],
            ["id"],
            ondelete="SET NULL",
        )
    except Exception:
        # Some DBs may not support self-referential FK or online creation; skip gracefully
        pass


def downgrade() -> None:
    try:
        op.drop_constraint("fk_users_owner_user_id_users", "users", type_="foreignkey")
    except Exception:
        pass
    op.drop_column("users", "can_manage_members")
    op.drop_column("users", "can_view_interviews")
    op.drop_column("users", "can_manage_candidates")
    op.drop_column("users", "can_manage_jobs")
    op.drop_column("users", "role")
    op.drop_column("users", "owner_user_id")


