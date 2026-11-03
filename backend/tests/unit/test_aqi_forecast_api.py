"""AQI model-B API: /air-quality/forecast, /air-quality/{region_id}/forecast, /models/current.

The forecast endpoints read wf.aqi_forecasts_b / wf.aqi_forecast_skips, so those tests need a
migrated throwaway Postgres in WF_TEST_DATABASE_URL (never prod) and are skipped without it.
"""

import json
import os
from datetime import date, timedelta
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_db
from app.core.config import settings
from app.main import app

MODEL_DIR = Path(__file__).resolve().parents[2] / "models" / settings.ACTIVE_AQI_MODEL
VERSION = settings.ACTIVE_AQI_MODEL
OLD, NEW = date(2026, 11, 1), date(2026, 11, 2)

TEST_DB = os.environ.get("WF_TEST_DATABASE_URL")
needs_db = pytest.mark.skipif(not TEST_DB, reason="WF_TEST_DATABASE_URL not set")


def test_models_current_aqi_entry_reads_training_files():
    ev = json.loads((MODEL_DIR / "aqi_station_evaluation.json").read_text(encoding="utf-8"))
    meta = json.loads((MODEL_DIR / "aqi_station_metadata.json").read_text(encoding="utf-8"))
    resp = TestClient(app).get("/api/v1/models/current")
    assert resp.status_code == 200
    aqi = [m for m in resp.json() if m["model_type"] == "aqi"]
    assert len(aqi) == 1
    m = aqi[0]
    assert (m["version"], m["status"], m["is_active"]) == (VERSION, "active", True)
    assert "persistence" not in json.dumps(m)
    for h in (1, 2, 3):
        rows = ev["test"][f"h{h}"]["all_rows_with_target"]
        assert m["metrics"]["test_mae"][f"h{h}"] == rows["no_station"]["mae"]
        assert m["metrics"]["raw_cams_mae"][f"h{h}"] == rows["cams_t"]["mae"]
    assert m["metrics"]["test_disclosure"] == meta["test_disclosure"]
    assert m["feature_list"] == meta["features"]["no_station"]


@pytest.fixture
async def db_factory():
    from sqlalchemy import delete, select
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.db.models.air_quality import AQIForecastB, AQIForecastSkip
    from app.db.models.region import Region

    assert TEST_DB is not None
    url = TEST_DB.replace("postgresql://", "postgresql+asyncpg://", 1)
    engine = create_async_engine(url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        if (await s.execute(select(Region.id).limit(1))).first() is not None:
            await engine.dispose()
            pytest.skip("test database already has regions; needs an empty throwaway DB")
        for rid in (1, 2, 3):
            s.add(
                Region(
                    id=rid,
                    state_name="test",
                    district_name=f"test{rid}",
                    gadm_id=f"TEST.{rid}",
                    landcover={},
                )
            )
        await s.flush()

        def fc(rid: int, origin: date, version: str = VERSION) -> list[AQIForecastB]:
            return [
                AQIForecastB(
                    region_id=rid,
                    origin_date=origin,
                    target_date=origin + timedelta(days=h),
                    horizon=h,
                    pm25_si_pred=100.0 + h + rid,
                    category="Moderate",
                    model_version=version,
                    source="model_b_no_station",
                    extrapolated=rid == 1,
                )
                for h in (1, 2, 3)
            ]

        # Region 1: old and new origin -> new one is served.
        s.add_all(fc(1, OLD) + fc(1, NEW))
        # Region 2: forecast at the old origin, skipped at the new one -> skip reason.
        s.add_all(fc(2, OLD))
        s.add(AQIForecastSkip(region_id=2, origin_date=NEW, model_version=VERSION, reason="r2"))
        # Region 3: rows only for another model version -> absent.
        s.add_all(fc(3, NEW, version="other_version"))
        await s.commit()

    async def override_db():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    yield factory
    app.dependency_overrides.pop(get_db, None)
    async with factory() as s:
        ids = [1, 2, 3]
        await s.execute(delete(AQIForecastB).where(AQIForecastB.region_id.in_(ids)))
        await s.execute(delete(AQIForecastSkip).where(AQIForecastSkip.region_id.in_(ids)))
        await s.execute(delete(Region).where(Region.gadm_id.like("TEST.%")))
        await s.commit()
    await engine.dispose()


async def _get(path: str) -> httpx.Response:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as c:
        return await c.get(path)


@needs_db
async def test_region_forecast_latest_origin(db_factory):
    resp = await _get("/api/v1/air-quality/1/forecast")
    assert resp.status_code == 200
    d = resp.json()
    assert (d["region_id"], d["status"], d["origin_date"]) == (1, "forecast", NEW.isoformat())
    assert (d["model_version"], d["source"], d["extrapolated"]) == (
        VERSION,
        "model_b_no_station",
        True,
    )
    assert d["skip_reason"] is None
    assert d["forecasts"] == [
        {
            "horizon": h,
            "target_date": (NEW + timedelta(days=h)).isoformat(),
            "pm25_si_pred": 101.0 + h,
            "category": "Moderate",
        }
        for h in (1, 2, 3)
    ]


@needs_db
async def test_region_forecast_skipped_returns_reason_not_values(db_factory):
    resp = await _get("/api/v1/air-quality/2/forecast")
    assert resp.status_code == 200
    d = resp.json()
    assert (d["status"], d["origin_date"], d["skip_reason"]) == ("skipped", NEW.isoformat(), "r2")
    assert d["forecasts"] == [] and d["source"] is None and d["extrapolated"] is None


@needs_db
async def test_region_forecast_missing_is_404(db_factory):
    assert (await _get("/api/v1/air-quality/3/forecast")).status_code == 404


@needs_db
async def test_all_forecasts(db_factory):
    resp = await _get("/api/v1/air-quality/forecast")
    assert resp.status_code == 200
    d = resp.json()
    assert d["model_version"] == VERSION
    assert d["counts"] == {"forecast": 1, "skipped": 1}
    assert [(x["region_id"], x["status"]) for x in d["districts"]] == [
        (1, "forecast"),
        (2, "skipped"),
    ]
    assert len(d["districts"][0]["forecasts"]) == 3
