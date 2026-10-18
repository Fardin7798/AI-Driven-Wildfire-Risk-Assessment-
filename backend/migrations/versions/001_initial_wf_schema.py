"""001_initial_wf_schema

Revision ID: 001_initial_wf_schema
Revises: 
Create Date: 2026-10-18 23:05:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from geoalchemy2 import Geometry

revision: str = '001_initial_wf_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. PostGIS Extension & Schema
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
    op.execute("CREATE SCHEMA IF NOT EXISTS wf;")

    # 2. Regions
    op.create_table(
        'regions',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('country_code', sa.String(length=3), nullable=False),
        sa.Column('admin_level', sa.Integer(), nullable=False),
        sa.Column('state_name', sa.String(length=100), nullable=False),
        sa.Column('district_name', sa.String(length=100), nullable=False),
        sa.Column('gadm_id', sa.String(length=50), nullable=False),
        sa.Column('geom', Geometry(geometry_type='MULTIPOLYGON', srid=4326, spatial_index=True), nullable=True),
        sa.Column('centroid', Geometry(geometry_type='POINT', srid=4326, spatial_index=True), nullable=True),
        sa.Column('area_km2', sa.Float(), nullable=True),
        sa.Column('landcover', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('timezone', sa.String(length=50), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_regions')),
        sa.UniqueConstraint('gadm_id', name=op.f('uq_regions_gadm_id')),
        schema='wf'
    )
    op.create_index(op.f('ix_wf_regions_country_code'), 'regions', ['country_code'], unique=False, schema='wf')
    op.create_index(op.f('ix_wf_regions_state_name'), 'regions', ['state_name'], unique=False, schema='wf')
    op.create_index(op.f('ix_wf_regions_district_name'), 'regions', ['district_name'], unique=False, schema='wf')

    # 3. Fire Detections
    op.create_table(
        'fire_detections',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('source', sa.String(length=50), nullable=False),
        sa.Column('satellite', sa.String(length=20), nullable=False),
        sa.Column('instrument', sa.String(length=20), nullable=False),
        sa.Column('acq_datetime_utc', sa.DateTime(timezone=True), nullable=False),
        sa.Column('lat', sa.Float(), nullable=False),
        sa.Column('lon', sa.Float(), nullable=False),
        sa.Column('geom', Geometry(geometry_type='POINT', srid=4326, spatial_index=True), nullable=True),
        sa.Column('brightness', sa.Float(), nullable=True),
        sa.Column('frp', sa.Float(), nullable=True),
        sa.Column('confidence', sa.String(length=20), nullable=True),
        sa.Column('daynight', sa.String(length=5), nullable=True),
        sa.Column('landcover_class', sa.String(length=50), nullable=True),
        sa.Column('region_id', sa.BigInteger(), nullable=True),
        sa.ForeignKeyConstraint(['region_id'], ['wf.regions.id'], name=op.f('fk_fire_detections_region_id_regions'), ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_fire_detections')),
        sa.UniqueConstraint('source', 'acq_datetime_utc', 'lat', 'lon', name='uq_fire_detections_source_time_lat_lon'),
        schema='wf'
    )
    op.create_index(op.f('ix_wf_fire_detections_acq_datetime_utc'), 'fire_detections', ['acq_datetime_utc'], unique=False, schema='wf')
    op.create_index(op.f('ix_wf_fire_detections_source'), 'fire_detections', ['source'], unique=False, schema='wf')

    # 4. Weather Daily & FWI State
    op.create_table(
        'weather_daily',
        sa.Column('region_id', sa.BigInteger(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('is_forecast', sa.Boolean(), nullable=False),
        sa.Column('temp_max', sa.Float(), nullable=True),
        sa.Column('temp_min', sa.Float(), nullable=True),
        sa.Column('temp_mean', sa.Float(), nullable=True),
        sa.Column('rh_mean', sa.Float(), nullable=True),
        sa.Column('rh_min', sa.Float(), nullable=True),
        sa.Column('wind_max', sa.Float(), nullable=True),
        sa.Column('precip_sum', sa.Float(), nullable=True),
        sa.Column('et0', sa.Float(), nullable=True),
        sa.Column('soil_moisture', sa.Float(), nullable=True),
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.ForeignKeyConstraint(['region_id'], ['wf.regions.id'], name=op.f('fk_weather_daily_region_id_regions'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('region_id', 'date', 'is_forecast', name=op.f('pk_weather_daily')),
        schema='wf'
    )

    op.create_table(
        'fwi_state',
        sa.Column('region_id', sa.BigInteger(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('ffmc', sa.Float(), nullable=False),
        sa.Column('dmc', sa.Float(), nullable=False),
        sa.Column('dc', sa.Float(), nullable=False),
        sa.Column('isi', sa.Float(), nullable=False),
        sa.Column('bui', sa.Float(), nullable=False),
        sa.Column('fwi', sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(['region_id'], ['wf.regions.id'], name=op.f('fk_fwi_state_region_id_regions'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('region_id', 'date', name=op.f('pk_fwi_state')),
        schema='wf'
    )

    # 5. Air Quality
    op.create_table(
        'aq_stations',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.Column('external_id', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('city', sa.String(length=100), nullable=False),
        sa.Column('state', sa.String(length=100), nullable=False),
        sa.Column('geom', Geometry(geometry_type='POINT', srid=4326, spatial_index=True), nullable=True),
        sa.Column('region_id', sa.BigInteger(), nullable=True),
        sa.ForeignKeyConstraint(['region_id'], ['wf.regions.id'], name=op.f('fk_aq_stations_region_id_regions'), ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_aq_stations')),
        schema='wf'
    )
    op.create_index(op.f('ix_wf_aq_stations_external_id'), 'aq_stations', ['external_id'], unique=False, schema='wf')

    op.create_table(
        'aq_observations',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('station_id', sa.BigInteger(), nullable=True),
        sa.Column('region_id', sa.BigInteger(), nullable=True),
        sa.Column('observed_at_utc', sa.DateTime(timezone=True), nullable=False),
        sa.Column('pm25', sa.Float(), nullable=True),
        sa.Column('pm10', sa.Float(), nullable=True),
        sa.Column('no2', sa.Float(), nullable=True),
        sa.Column('so2', sa.Float(), nullable=True),
        sa.Column('co', sa.Float(), nullable=True),
        sa.Column('o3', sa.Float(), nullable=True),
        sa.Column('nh3', sa.Float(), nullable=True),
        sa.Column('aqi', sa.Integer(), nullable=True),
        sa.Column('aqi_category', sa.String(length=50), nullable=True),
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.ForeignKeyConstraint(['region_id'], ['wf.regions.id'], name=op.f('fk_aq_observations_region_id_regions'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['station_id'], ['wf.aq_stations.id'], name=op.f('fk_aq_observations_station_id_aq_stations'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_aq_observations')),
        sa.UniqueConstraint('provider', 'station_id', 'region_id', 'observed_at_utc', name='uq_aq_obs_provider_station_region_time'),
        schema='wf'
    )
    op.create_index(op.f('ix_wf_aq_observations_observed_at_utc'), 'aq_observations', ['observed_at_utc'], unique=False, schema='wf')

    op.create_table(
        'aq_forecasts',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('region_id', sa.BigInteger(), nullable=False),
        sa.Column('target_date', sa.Date(), nullable=False),
        sa.Column('horizon_days', sa.Integer(), nullable=False),
        sa.Column('pm25_pred', sa.Float(), nullable=True),
        sa.Column('aqi_pred', sa.Integer(), nullable=True),
        sa.Column('aqi_category', sa.String(length=50), nullable=True),
        sa.Column('model_version', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['region_id'], ['wf.regions.id'], name=op.f('fk_aq_forecasts_region_id_regions'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_aq_forecasts')),
        schema='wf'
    )

    # 6. Risk Predictions
    op.create_table(
        'risk_predictions',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('region_id', sa.BigInteger(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('probability', sa.Float(), nullable=False),
        sa.Column('risk_class', sa.String(length=20), nullable=False),
        sa.Column('model_version', sa.String(length=50), nullable=False),
        sa.Column('fwi_value', sa.Float(), nullable=False),
        sa.Column('top_factors', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['region_id'], ['wf.regions.id'], name=op.f('fk_risk_predictions_region_id_regions'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_risk_predictions')),
        sa.UniqueConstraint('region_id', 'date', 'model_version', name='uq_risk_predictions_region_date_model'),
        schema='wf'
    )
    op.create_index(op.f('ix_wf_risk_predictions_date'), 'risk_predictions', ['date'], unique=False, schema='wf')
    op.create_index(op.f('ix_wf_risk_predictions_risk_class'), 'risk_predictions', ['risk_class'], unique=False, schema='wf')

    # 7. Model Registry
    op.create_table(
        'model_versions',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('model_type', sa.String(length=20), nullable=False),
        sa.Column('version', sa.String(length=50), nullable=False),
        sa.Column('trained_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('metrics', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('feature_list', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('thresholds', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('artifact_path', sa.String(length=255), nullable=False),
        sa.Column('sha256', sa.String(length=64), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_model_versions')),
        sa.UniqueConstraint('version', name=op.f('uq_model_versions_version')),
        schema='wf'
    )
    op.create_index(op.f('ix_wf_model_versions_is_active'), 'model_versions', ['is_active'], unique=False, schema='wf')
    op.create_index(op.f('ix_wf_model_versions_model_type'), 'model_versions', ['model_type'], unique=False, schema='wf')

    # 8. Ingestion Runs
    op.create_table(
        'ingestion_runs',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('job_name', sa.String(length=100), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('rows_written', sa.Integer(), nullable=False),
        sa.Column('error', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_ingestion_runs')),
        schema='wf'
    )
    op.create_index(op.f('ix_wf_ingestion_runs_job_name'), 'ingestion_runs', ['job_name'], unique=False, schema='wf')

    # 9. Preparedness Items
    op.create_table(
        'preparedness_items',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('hazard', sa.String(length=20), nullable=False),
        sa.Column('stage', sa.String(length=20), nullable=False),
        sa.Column('audience', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('source_url', sa.String(length=255), nullable=False),
        sa.Column('lang', sa.String(length=10), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_preparedness_items')),
        schema='wf'
    )
    op.create_index(op.f('ix_wf_preparedness_items_hazard'), 'preparedness_items', ['hazard'], unique=False, schema='wf')
    op.create_index(op.f('ix_wf_preparedness_items_stage'), 'preparedness_items', ['stage'], unique=False, schema='wf')

    # 10. Security: Enable Row Level Security & Revoke Privileges on schema wf
    tables = [
        "regions", "fire_detections", "weather_daily", "fwi_state",
        "aq_stations", "aq_observations", "aq_forecasts", "risk_predictions",
        "model_versions", "ingestion_runs", "preparedness_items"
    ]
    for tbl in tables:
        op.execute(f"ALTER TABLE wf.{tbl} ENABLE ROW LEVEL SECURITY;")

    # Revoke default privileges from anon and authenticated on schema wf
    op.execute("DO $$ BEGIN "
               "IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN "
               "  REVOKE ALL ON SCHEMA wf FROM anon; "
               "  REVOKE ALL ON ALL TABLES IN SCHEMA wf FROM anon; "
               "END IF; "
               "IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN "
               "  REVOKE ALL ON SCHEMA wf FROM authenticated; "
               "  REVOKE ALL ON ALL TABLES IN SCHEMA wf FROM authenticated; "
               "END IF; "
               "END $$;")


def downgrade() -> None:
    tables = [
        "preparedness_items", "ingestion_runs", "model_versions",
        "risk_predictions", "aq_forecasts", "aq_observations", "aq_stations",
        "fwi_state", "weather_daily", "fire_detections", "regions"
    ]
    for tbl in tables:
        op.drop_table(tbl, schema='wf')
    op.execute("DROP SCHEMA IF EXISTS wf CASCADE;")
