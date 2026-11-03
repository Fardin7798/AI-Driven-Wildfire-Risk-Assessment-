"""Add wf.aqi_forecasts_b and wf.aqi_forecast_skips (AQI model B daily forecasts).

Non-destructive: wf.aq_forecasts (persistence baseline rows) is left as it is.

Revision ID: 003_aqi_forecasts_b
Revises: 002_drop_model_versions
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "003_aqi_forecasts_b"
down_revision: str | None = "002_drop_model_versions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "aqi_forecasts_b",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("region_id", sa.BigInteger(), nullable=False),
        sa.Column("origin_date", sa.Date(), nullable=False),
        sa.Column("target_date", sa.Date(), nullable=False),
        sa.Column("horizon", sa.Integer(), nullable=False),
        sa.Column("pm25_si_pred", sa.Float(), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("model_version", sa.String(length=50), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("extrapolated", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("horizon BETWEEN 1 AND 3", name=op.f("ck_aqi_forecasts_b_horizon")),
        sa.ForeignKeyConstraint(
            ["region_id"],
            ["wf.regions.id"],
            name="fk_aqi_forecasts_b_region_id_regions",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_aqi_forecasts_b"),
        sa.UniqueConstraint(
            "region_id",
            "origin_date",
            "horizon",
            "model_version",
            name="uq_aqi_forecasts_b_region_origin_horizon_version",
        ),
        schema="wf",
    )
    op.create_index(
        "ix_wf_aqi_forecasts_b_region_id", "aqi_forecasts_b", ["region_id"], schema="wf"
    )
    op.create_index(
        "ix_wf_aqi_forecasts_b_target_date", "aqi_forecasts_b", ["target_date"], schema="wf"
    )

    op.create_table(
        "aqi_forecast_skips",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("region_id", sa.BigInteger(), nullable=False),
        sa.Column("origin_date", sa.Date(), nullable=False),
        sa.Column("model_version", sa.String(length=50), nullable=False),
        sa.Column("reason", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["region_id"],
            ["wf.regions.id"],
            name="fk_aqi_forecast_skips_region_id_regions",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_aqi_forecast_skips"),
        sa.UniqueConstraint(
            "region_id",
            "origin_date",
            "model_version",
            name="uq_aqi_forecast_skips_region_origin_version",
        ),
        schema="wf",
    )
    op.create_index(
        "ix_wf_aqi_forecast_skips_region_id", "aqi_forecast_skips", ["region_id"], schema="wf"
    )
    op.create_index(
        "ix_wf_aqi_forecast_skips_origin_date",
        "aqi_forecast_skips",
        ["origin_date"],
        schema="wf",
    )

    for tbl in ("aqi_forecasts_b", "aqi_forecast_skips"):
        op.execute(f"ALTER TABLE wf.{tbl} ENABLE ROW LEVEL SECURITY;")
        op.execute(
            "DO $$ BEGIN "
            "IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN "
            f"  REVOKE ALL ON wf.{tbl} FROM anon; "
            "END IF; "
            "IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN "
            f"  REVOKE ALL ON wf.{tbl} FROM authenticated; "
            "END IF; "
            "END $$;"
        )


def downgrade() -> None:
    op.drop_table("aqi_forecast_skips", schema="wf")
    op.drop_table("aqi_forecasts_b", schema="wf")
