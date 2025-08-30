"""add unique partial index to dedupe assistant duplicate messages

Revision ID: add_unique_assistant_msg_idx
Revises: add_extra_questions_jobs2
Create Date: 2025-08-30 01:15:00.000000

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = 'add_unique_assistant_msg_idx'
down_revision = 'add_extra_questions_jobs2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Deduplicate assistant messages by content per interview.
    # Predicate must avoid functions on the column to satisfy Postgres IMMUTABLE requirement.
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_assistant_msg_content
        ON conversation_messages (interview_id, content)
        WHERE role = 'ASSISTANT'::messagerole;
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_assistant_msg_content;")


