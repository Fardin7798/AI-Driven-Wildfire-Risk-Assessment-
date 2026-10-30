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
    assert "db" in data
    assert data["db"] in ["ok", "down"]
    assert "supabase" not in str(data).lower()

    # Test /api/v1/health
    resp_v1 = client.get("/api/v1/health")
    assert resp_v1.status_code == 200
    data_v1 = resp_v1.json()
    assert data_v1["status"] == "ok"
    assert data_v1["version"] == settings.APP_VERSION
    assert "db" in data_v1
    assert data_v1["db"] in ["ok", "down"]


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

    for m in models:
        assert m["status"] in ["active", "awaiting_training"]
        if m["status"] == "awaiting_training":
            assert m["metrics"] is None

    resp_comp = client.get("/api/v1/models/comparison")
    assert resp_comp.status_code == 200
    comp_data = resp_comp.json()
    assert comp_data["status"] in ["available", "not_available"]
    assert isinstance(comp_data["models"], list)


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


def test_geo_cities_search():
    import httpx
    import respx

    with respx.mock(base_url="https://nominatim.openstreetmap.org") as respx_mock:
        respx_mock.get("/search").mock(
            return_value=httpx.Response(
                200,
                json=[
                    {
                        "name": "Varangaon",
                        "lat": "21.0104777",
                        "lon": "75.9013224",
                        "display_name": "Varangaon, Bhusawal, Jalgaon, Maharashtra, 425305, India",
                        "address": {
                            "county": "Jalgaon",
                            "state": "Maharashtra",
                        },
                    }
                ],
            )
        )
        resp = client.get("/api/v1/geo/cities?q=varangaon&limit=5")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["name"] == "Varangaon"
        assert data[0]["lat"] == 21.0104777
        assert data[0]["lon"] == 75.9013224
        assert data[0]["state"] == "Maharashtra"
        assert data[0]["district"] == "Jalgaon"
        assert "display_name" in data[0]


def test_regions_by_coordinates():
    resp = client.get("/api/v1/regions/by-coordinates")
    assert resp.status_code == 422
