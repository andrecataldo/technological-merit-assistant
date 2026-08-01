"""Add documents table."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002_add_documents"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("evaluation_id", sa.Uuid(), nullable=False),
        sa.Column(
            "original_filename",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "storage_key",
            sa.String(),
            nullable=False,
        ),
        sa.Column(
            "content_type",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "size_bytes",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "sha256",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.CheckConstraint(
            "size_bytes > 0",
            name="ck_documents_size_bytes_positive",
        ),
        sa.CheckConstraint(
            "char_length(sha256) = 64",
            name="ck_documents_sha256_length",
        ),
        sa.ForeignKeyConstraint(
            ["evaluation_id"],
            ["evaluations.id"],
            name="fk_documents_evaluation_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "evaluation_id",
            "sha256",
            name="uq_documents_evaluation_sha256",
        ),
        sa.UniqueConstraint(
            "storage_key",
            name="uq_documents_storage_key",
        ),
    )

    op.create_index(
        "ix_documents_evaluation_id",
        "documents",
        ["evaluation_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_documents_evaluation_id",
        table_name="documents",
    )
    op.drop_table("documents")
