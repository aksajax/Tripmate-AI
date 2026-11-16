
"""Add persistent idempotency records.

Revision ID: 20261024_1200
Revises: ac7f1aa4d10c
Create Date: 2026-10-24
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20261024_1200"
down_revision = "ac7f1aa4d10c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the idempotency records table."""
    op.create_table(
        "idempotency_records",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("key", sa.String(length=128), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("response_status", sa.Integer(), nullable=False),
        sa.Column(
            "response_body",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "key",
            name="uq_idempotency_records_user_key",
        ),
    )

    op.create_index(
        "ix_idempotency_records_created_at",
        "idempotency_records",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    """Remove the idempotency records table."""
    op.drop_index(
        "ix_idempotency_records_created_at",
        table_name="idempotency_records",
    )
    op.drop_table("idempotency_records")
