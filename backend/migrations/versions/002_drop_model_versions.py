"""Drop wf.model_versions.

The table was never read by the API (served models are described by the JSON files in
backend/models) and only held rows for deleted v1 artifacts.

Revision ID: 002_drop_model_versions
Revises: 001_initial_wf_schema
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "002_drop_model_versions"
down_revision: str | None = "001_initial_wf_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_index("ix_wf_model_versions_model_type", table_name="model_versions", schema="wf")
    op.drop_index("ix_wf_model_versions_is_active", table_name="model_versions", schema="wf")
    op.drop_table("model_versions", schema="wf")


def downgrade() -> None:
    op.create_table(
        "model_versions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("model_type", sa.String(length=20), nullable=False),
        sa.Column("version", sa.String(length=50), nullable=False),
        sa.Column("trained_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metrics", postgresql.JSONB(), nullable=False),
        sa.Column("feature_list", postgresql.JSONB(), nullable=False),
        sa.Column("thresholds", postgresql.JSONB(), nullable=False),
        sa.Column("artifact_path", sa.String(length=255), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_model_versions"),
        sa.UniqueConstraint("version", name="uq_model_versions_version"),
        schema="wf",
    )
    op.create_index(
        "ix_wf_model_versions_is_active", "model_versions", ["is_active"], schema="wf"
    )
    op.create_index(
        "ix_wf_model_versions_model_type", "model_versions", ["model_type"], schema="wf"
    )
    op.execute("ALTER TABLE wf.model_versions ENABLE ROW LEVEL SECURITY;")
