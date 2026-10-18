from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from app.api.deps import get_db
from app.core.config import settings
from app.main import app


async def _override_get_db():
    mock = AsyncMock()
    mock.execute.side_effect = Exception("DB offline in unit test")
    yield mock


app.dependency_overrides[get_db] = _override_get_db

client = TestClient(app)


def test_health_endpoints():
    # Test root /health
    resp_root = client.get("/health")
    assert resp_root.status_code == 200
    data = resp_root.json()
    assert data["status"] == "ok"
    assert data["version"] == settings.APP_VERSION
    # Must not leak project refs or database host details
    assert "db" not in data
    assert "supabase" not in str(data).lower()

    # Test /api/v1/health
    resp_v1 = client.get("/api/v1/health")
    assert resp_v1.status_code == 200
    assert resp_v1.json() == data


def test_meta_sources_and_attribution():
    resp = client.get("/api/v1/meta/sources")
    assert resp.status_code == 200
    data = resp.json()
    assert "sources" in data
    sources = data["sources"]
    source_names = [s["name"] for s in sources]
    assert any("FIRMS" in name for name in source_names)
    assert any("Open-Meteo" in name for name in source_names)
    assert any("CPCB" in name for name in source_names)
    assert any("GADM" in name for name in source_names)
    assert any("WorldCover" in name for name in source_names)


def test_meta_disclaimer():
    resp = client.get("/api/v1/meta/disclaimer")
    assert resp.status_code == 200
    data = resp.json()
    assert "disclaimer" in data
    assert "academic_mandate" in data
    assert "official_authorities" in data
    assert "India Meteorological Department (IMD)" in data["official_authorities"]
    assert "Central Pollution Control Board (CPCB)" in data["official_authorities"]
    assert "National Disaster Management Authority (NDMA)" in data["official_authorities"]


def test_models_current_and_comparison():
    resp_cur = client.get("/api/v1/models/current")
    assert resp_cur.status_code == 200
    models = resp_cur.json()
    assert len(models) >= 1
    types = [m["model_type"] for m in models]
    assert "wildfire" in types

    resp_comp = client.get("/api/v1/models/comparison")
    assert resp_comp.status_code == 200
    comp_data = resp_comp.json()
    assert "wildfire_comparison" in comp_data
    assert "aqi_comparison" in comp_data
    wf_models = comp_data["wildfire_comparison"]["models"]
    model_names = [m["name"] for m in wf_models]
    assert any("XGBoost" in name for name in model_names)
    assert any("Random Forest" in name for name in model_names)
    assert any("Canadian FWI" in name for name in model_names)


def test_internal_job_token_security():
    # Calling internal job without token must fail with 401 or 422
    resp_no_token = client.post("/api/v1/internal/jobs/ingest_fires")
    assert resp_no_token.status_code in [401, 422]

    # Calling with invalid token must fail with 401
    resp_bad_token = client.post(
        "/api/v1/internal/jobs/ingest_fires",
        headers={"X-Job-Token": "invalid_secret_token_123"},
    )
    assert resp_bad_token.status_code == 401

    # Calling with valid token but non-existent job must return 404
    resp_unknown_job = client.post(
        "/api/v1/internal/jobs/non_existent_job",
        headers={"X-Job-Token": settings.JOB_TOKEN},
    )
    assert resp_unknown_job.status_code == 404
