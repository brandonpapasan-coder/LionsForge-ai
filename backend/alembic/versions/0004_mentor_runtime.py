"""add mentor runtime persistence

Revision ID: 0004_mentor_runtime
Revises: 0003_company_intelligence
Create Date: 2026-07-10 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_mentor_runtime"
down_revision: str | None = "0003_company_intelligence"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "mentor_conversations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("active_context", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_mentor_conversations_user_updated", "mentor_conversations", ["user_id", "updated_at"], unique=False)
    op.create_table(
        "mentor_messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("conversation_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=24), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("intent", sa.String(length=48), nullable=True),
        sa.Column("persona", sa.String(length=48), nullable=True),
        sa.Column("response_payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["mentor_conversations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_mentor_messages_conversation_created", "mentor_messages", ["conversation_id", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_mentor_messages_conversation_created", table_name="mentor_messages")
    op.drop_table("mentor_messages")
    op.drop_index("ix_mentor_conversations_user_updated", table_name="mentor_conversations")
    op.drop_table("mentor_conversations")
