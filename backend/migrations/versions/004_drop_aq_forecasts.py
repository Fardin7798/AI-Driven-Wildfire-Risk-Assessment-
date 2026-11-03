"""Drop wf.aq_forecasts.

The table held rows of the removed persistence baseline (aqi_persistence_v1). Since
003 the forecast_aqi job writes model B forecasts to wf.aqi_forecasts_b and the API
reads only that table, so wf.aq_forecasts is neither read nor written. Its rows were
exported before this change (outside the repository). Downgrade recreates the empty
table with the schema from 001 (rows are not restored).

Revision ID: 004_drop_aq_forecasts
Revises: 003_aqi_forecasts_b
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "004_drop_aq_forecasts"
down_revision: str | None = "003_aqi_forecasts_b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_table("aq_forecasts", schema="wf")


def downgrade() -> None:
    op.create_table(
        "aq_forecasts",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("region_id", sa.BigInteger(), nullable=False),
        sa.Column("target_date", sa.Date(), nullable=False),
        sa.Column("horizon_days", sa.Integer(), nullable=False),
        sa.Column("pm25_pred", sa.Float(), nullable=True),
        sa.Column("aqi_pred", sa.Integer(), nullable=True),
        sa.Column("aqi_category", sa.String(length=50), nullable=True),
        sa.Column("model_version", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["region_id"],
            ["wf.regions.id"],
            name="fk_aq_forecasts_region_id_regions",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_aq_forecasts"),
        schema="wf",
    )
    op.execute("ALTER TABLE wf.aq_forecasts ENABLE ROW LEVEL SECURITY;")
    op.execute(
        "DO $$ BEGIN "
        "IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN "
        "  REVOKE ALL ON wf.aq_forecasts FROM anon; "
        "END IF; "
        "IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN "
        "  REVOKE ALL ON wf.aq_forecasts FROM authenticated; "
        "END IF; "
        "END $$;"
    )
