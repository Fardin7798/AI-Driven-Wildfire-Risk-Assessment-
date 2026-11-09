"""forecast_aqi job (AQI model B for every district): network is mocked everywhere.

The control-flow tests use a fake session. The persistence tests need a migrated throwaway
Postgres in WF_TEST_DATABASE_URL (never prod) and are skipped without it.
"""

import os
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pytest

pd = pytest.importorskip("pandas")

from app.domain.aqi_features import HISTORY_DAYS, WEATHER_DAILY  # noqa: E402
from app.jobs import forecast_aqi as fj  # noqa: E402
from app.ml import aqi_station_b as sb  # noqa: E402
from app.ml.loader import ModelLoader  # noqa: E402
from app.providers.open_meteo_http import OpenMeteoQuotaExceeded  # noqa: E402

MODEL_DIR = Path(__file__).resolve().parents[2] / "models"
VERSION = "aqi_station_xgb_v3"
ORIGIN = date(2026, 11, 2)
# Training centroids of regions 1 and 2 (coverage.json).
R1 = (1, 7.5254, 93.5992)
R2 = (2, 12.8529, 92.8728)


@pytest.fixture(scope="module")
def model():
    m = ModelLoader(str(MODEL_DIR)).load_aqi_model(VERSION)
    assert m is not None
    return m


def _payloads(origin: date, hours_missing_on_origin: int = 0) -> tuple[dict, dict]:
    first = origin - timedelta(days=HISTORY_DAYS)
    times = pd.date_range(str(first), periods=24 * (HISTORY_DAYS + 1), freq="h")
    base = {"pm2_5": 50.0, "pm10": 80.0, "nitrogen_dioxide": 20.0}
    base |= {"sulphur_dioxide": 10.0, "carbon_monoxide": 800.0, "ozone": 40.0}
    hourly: dict = {"time": list(times.strftime("%Y-%m-%dT%H:%M"))}
    for k, v in base.items():
        col: list[Any] = [v] * len(times)
        for i in range(hours_missing_on_origin):
            col[-1 - i] = None
        hourly[k] = col
    days = [str(origin - timedelta(days=d)) for d in (2, 1, 0)] + [str(origin + timedelta(1))]
    daily: dict = {"time": days}
    for om in WEATHER_DAILY:
        daily[om] = [20.0, 21.0, 22.0, 23.0]
    return hourly, daily


def _fake_get_json(hours_missing_on_origin: int = 0, quota_after: int | None = None):
    hourly, daily = _payloads(ORIGIN, hours_missing_on_origin)
    calls = {"n": 0}

    async def fake(url: str, params: dict[str, Any]) -> Any:
        calls["n"] += 1
        if quota_after is not None and calls["n"] > quota_after:
            raise OpenMeteoQuotaExceeded("Hourly API request limit exceeded")
        one = {"hourly": hourly} if "hourly" in params else {"daily": daily}
        n = str(params["latitude"]).count(",") + 1
        return one if n == 1 else [one] * n

    return fake, calls


# ---------------------------------------------------------------- control flow (fake session)
class _Result:
    def first(self) -> None:
        return None


class FakeSession:
    def __init__(self) -> None:
        self.statements: list[Any] = []
        self.commits = 0

    async def __aenter__(self) -> "FakeSession":
        return self

    async def __aexit__(self, *exc: object) -> None:
        return None

    async def execute(self, stmt: Any) -> _Result:
        self.statements.append(stmt)
        return _Result()

    async def commit(self) -> None:
        self.commits += 1

    def table_ops(self, table: str, kind: str) -> int:
        return sum(
            1
            for s in self.statements
            if getattr(getattr(s, "table", None), "name", None) == table
            and type(s).__name__.lower().startswith(kind)
        )


@pytest.fixture
def fake_session(monkeypatch):
    session = FakeSession()
    monkeypatch.setattr(fj, "async_session_factory", lambda: session)
    return session


def _regions(rows):
    async def fake(session):
        return rows

    return fake


async def test_job_writes_forecasts_and_skips(model, monkeypatch, fake_session):
    fake, _ = _fake_get_json()
    monkeypatch.setattr(sb, "get_json", fake)
    monkeypatch.setattr(fj, "_regions", _regions([R1, (R2[0], 12.9, 92.8728), (3, None, None)]))

    stats = await fj.run_forecast_aqi(model, ORIGIN)

    assert stats == {
        "regions": 3,
        "forecast_regions": 1,
        "rows_written": 3,
        "skipped": 2,
        "skipped_kept_previous_forecast": 0,
    }
    assert fake_session.table_ops("aqi_forecasts_b", "insert") == 3
    assert fake_session.table_ops("aqi_forecast_skips", "insert") == 2
    assert fake_session.table_ops("aqi_forecast_skips", "delete") == 1
    assert fake_session.commits >= 1


async def test_job_raises_on_quota_and_commits_finished_work(model, monkeypatch, fake_session):
    # Batch 1 (50 districts, R1 among them) uses 2 calls; batch 2 (R2) hits the quota.
    fake, calls = _fake_get_json(quota_after=2)
    monkeypatch.setattr(sb, "get_json", fake)
    filler = [(1000 + i, None, None) for i in range(fj.COMMIT_EVERY - 1)]
    monkeypatch.setattr(fj, "_regions", _regions([R1, *filler, R2]))

    with pytest.raises(OpenMeteoQuotaExceeded):
        await fj.run_forecast_aqi(model, ORIGIN)

    assert calls["n"] == 3  # stopped at the first quota error, no retries
    assert fake_session.table_ops("aqi_forecasts_b", "insert") == 3
    assert fake_session.table_ops("aqi_forecast_skips", "insert") == fj.COMMIT_EVERY - 1
    assert fake_session.commits >= 1


async def test_batch_inputs_match_single_requests(model, monkeypatch):
    """A batched district gets the same forecast as one fetched on its own."""
    fake, calls = _fake_get_json()
    monkeypatch.setattr(sb, "get_json", fake)
    single = await sb.forecast_district(R1[0], R1[1], R1[2], model=model, origin=ORIGIN)
    fetched = await sb.fetch_inputs_batch([(R1[1], R1[2]), (R1[1], R1[2])], ORIGIN)
    batched = await sb.forecast_district(
        R1[0], R1[1], R1[2], model=model, origin=ORIGIN, inputs=fetched[0]
    )
    assert single["status"] == batched["status"] == "ok"
    assert single["forecasts"] == batched["forecasts"]
    assert calls["n"] == 4  # 2 single + 2 batch


async def test_job_fails_without_model(monkeypatch):
    monkeypatch.setattr(fj.model_loader, "load_aqi_model", lambda *a, **k: None)
    with pytest.raises(RuntimeError, match="not loaded"):
        await fj.job_forecast_aqi.__wrapped__()


def test_job_registered_and_scheduled_in_github_actions(monkeypatch):
    """forecast_aqi is triggerable, runs from GitHub Actions at 10:30 IST, and not on Render."""
    import importlib
    from pathlib import Path

    from app.api.v1.internal_jobs import JOB_MAPPING

    # app.jobs re-exports the APScheduler instance as `scheduler`, shadowing the module name.
    sched_mod = importlib.import_module("app.jobs.scheduler")

    assert JOB_MAPPING["forecast_aqi"] is fj.job_forecast_aqi
    added: dict[str, dict[str, Any]] = {}

    def add_job(func, trigger, id, **kw):
        added[id] = {"func": func, **kw}

    monkeypatch.setattr(sched_mod.settings, "ENABLE_SCHEDULER", True)
    monkeypatch.setattr(sched_mod.scheduler, "add_job", add_job)
    monkeypatch.setattr(sched_mod.scheduler, "start", lambda: None)
    sched_mod.start_scheduler()
    # Open-Meteo jobs must not run on Render's shared IP (daily quota).
    for name in ("forecast_aqi", "ingest_weather", "update_fwi_state", "predict_risk"):
        assert f"job_{name}" not in added
    assert {"job_ingest_fires", "job_ingest_air_quality", "job_retention"} <= set(added)

    wf = Path(__file__).resolve().parents[3] / ".github" / "workflows" / "pipeline-jobs.yml"
    text = wf.read_text()
    assert 'cron: "0 5 * * *"' in text  # 05:00 UTC = 10:30 IST
    assert 'echo "jobs=--unless-succeeded-within=12 forecast_aqi"' in text
    assert (
        'echo "jobs=--unless-succeeded-within=12 ingest_weather update_fwi_state predict_risk"'
        in text
    )
    assert "python -m app.jobs.cli" in text
    # No dispatch token: Render adds no dispatch jobs.
    assert not any(k.startswith("dispatch_") for k in added)


def test_render_dispatches_github_jobs_on_time(monkeypatch):
    """With a token, Render's scheduler starts the GitHub jobs at 00:20, 06:20/12:20, 10:30 IST."""
    import importlib

    sched_mod = importlib.import_module("app.jobs.scheduler")
    added: dict[str, dict[str, Any]] = {}

    def add_job(func, trigger, id, **kw):
        added[id] = kw

    monkeypatch.setattr(sched_mod.settings, "ENABLE_SCHEDULER", True)
    monkeypatch.setattr(sched_mod.settings, "GITHUB_DISPATCH_TOKEN", "t")
    monkeypatch.setattr(sched_mod.scheduler, "add_job", add_job)
    monkeypatch.setattr(sched_mod.scheduler, "start", lambda: None)
    sched_mod.start_scheduler()
    assert (added["dispatch_daily_chain"]["hour"], added["dispatch_daily_chain"]["minute"]) == (
        0,
        20,
    )
    assert added["dispatch_weather_retry"]["hour"] == "6,12"
    assert (added["dispatch_forecast_aqi"]["hour"], added["dispatch_forecast_aqi"]["minute"]) == (
        10,
        30,
    )


async def test_github_dispatch_posts_jobs(monkeypatch):
    from app.jobs import github_dispatch as gd

    sent: dict[str, Any] = {}

    class Resp:
        status_code = 204
        text = ""

    class Client:
        def __init__(self, *a: Any, **k: Any) -> None: ...

        async def __aenter__(self) -> "Client":
            return self

        async def __aexit__(self, *e: object) -> None: ...

        async def post(self, url: str, headers: dict[str, str], json: dict[str, Any]) -> Resp:
            sent.update(url=url, auth=headers["Authorization"], body=json)
            return Resp()

    monkeypatch.setattr(gd.settings, "GITHUB_DISPATCH_TOKEN", "tok")
    monkeypatch.setattr(gd.httpx, "AsyncClient", Client)
    assert await gd.dispatch_pipeline_jobs("forecast_aqi") is True
    assert sent["url"].endswith("/actions/workflows/pipeline-jobs.yml/dispatches")
    assert sent["auth"] == "Bearer tok"
    assert sent["body"] == {"ref": "main", "inputs": {"jobs": "forecast_aqi"}}

    monkeypatch.setattr(gd.settings, "GITHUB_DISPATCH_TOKEN", "")
    assert await gd.dispatch_pipeline_jobs("forecast_aqi") is False


async def test_cli_skips_when_recent_success(monkeypatch):
    from app.jobs import cli

    ran: list[str] = []

    async def handler() -> int:
        ran.append("x")
        return 1

    monkeypatch.setitem(cli.JOB_MAPPING, "ingest_weather", handler)

    async def yes(name: str, hours: float) -> bool:
        return True

    async def no(name: str, hours: float) -> bool:
        return False

    monkeypatch.setattr(cli, "_succeeded_within", yes)
    assert await cli._run(["--unless-succeeded-within=12", "ingest_weather"]) == 0
    assert ran == []
    monkeypatch.setattr(cli, "_succeeded_within", no)
    assert await cli._run(["--unless-succeeded-within=12", "ingest_weather"]) == 0
    assert ran == ["x"]


async def test_cli_skip_is_per_job(monkeypatch):
    """2026-11-09 regression: a skipped ingest_weather must not skip FWI and risk."""
    from app.jobs import cli

    ran: list[str] = []

    def make(name: str):
        async def handler() -> int:
            ran.append(name)
            return 1

        return handler

    for n in ("ingest_weather", "update_fwi_state", "predict_risk"):
        monkeypatch.setitem(cli.JOB_MAPPING, n, make(n))

    async def only_weather(name: str, hours: float) -> bool:
        return name == "ingest_weather"

    monkeypatch.setattr(cli, "_succeeded_within", only_weather)
    args = ["--unless-succeeded-within=12", "ingest_weather", "update_fwi_state", "predict_risk"]
    assert await cli._run(args) == 0
    assert ran == ["update_fwi_state", "predict_risk"]


# ---------------------------------------------------------------- persistence (real Postgres)
TEST_DB = os.environ.get("WF_TEST_DATABASE_URL")
needs_db = pytest.mark.skipif(not TEST_DB, reason="WF_TEST_DATABASE_URL not set")


@pytest.fixture
async def db_factory(monkeypatch):
    from sqlalchemy import delete, select, text
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.db.models.region import Region

    assert TEST_DB is not None
    url = TEST_DB.replace("postgresql://", "postgresql+asyncpg://", 1)
    engine = create_async_engine(url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        if (await s.execute(select(Region.id).limit(1))).first() is not None:
            await engine.dispose()
            pytest.skip("test database already has regions; needs an empty throwaway DB")
        for rid, lat, lon in (R1, (R2[0], 12.9, 92.8728), (3, None, None)):
            s.add(
                Region(
                    id=rid,
                    state_name="test",
                    district_name=f"test{rid}",
                    gadm_id=f"TEST.{rid}",
                    landcover={},
                    centroid=None if lat is None else f"SRID=4326;POINT({lon} {lat})",
                )
            )
        await s.commit()
    monkeypatch.setattr(fj, "async_session_factory", factory)
    yield factory, text
    async with factory() as s:
        await s.execute(delete(Region).where(Region.gadm_id.like("TEST.%")))
        await s.commit()
    await engine.dispose()


async def _rows(factory, text, sql: str) -> list[tuple]:
    async with factory() as s:
        return [tuple(r) for r in (await s.execute(text(sql))).all()]


@needs_db
async def test_job_persists_upserts_and_skips(model, monkeypatch, db_factory):
    factory, text = db_factory
    fake, _ = _fake_get_json()
    monkeypatch.setattr(sb, "get_json", fake)

    stats = await fj.run_forecast_aqi(model, ORIGIN)
    assert (stats["rows_written"], stats["skipped"]) == (3, 2)
    fc = await _rows(
        factory,
        text,
        "SELECT region_id, origin_date, target_date, horizon, source, extrapolated, model_version"
        " FROM wf.aqi_forecasts_b ORDER BY horizon",
    )
    assert fc == [
        (1, ORIGIN, ORIGIN + timedelta(days=h), h, "model_b_no_station", True, VERSION)
        for h in (1, 2, 3)
    ]
    skips = await _rows(
        factory, text, "SELECT region_id, reason FROM wf.aqi_forecast_skips ORDER BY region_id"
    )
    assert [s[0] for s in skips] == [2, 3]
    assert "training centroid" in skips[0][1] and skips[1][1] == "region has no centroid"

    # Same run again: upsert, no duplicates.
    await fj.run_forecast_aqi(model, ORIGIN)
    assert (await _rows(factory, text, "SELECT count(*) FROM wf.aqi_forecasts_b"))[0][0] == 3
    assert (await _rows(factory, text, "SELECT count(*) FROM wf.aqi_forecast_skips"))[0][0] == 2

    # A re-run with incomplete inputs keeps the forecast from complete inputs and adds no skip.
    fake, _ = _fake_get_json(hours_missing_on_origin=9)
    monkeypatch.setattr(sb, "get_json", fake)
    stats = await fj.run_forecast_aqi(model, ORIGIN)
    assert stats["skipped_kept_previous_forecast"] == 1
    assert (await _rows(factory, text, "SELECT count(*) FROM wf.aqi_forecasts_b"))[0][0] == 3
    regions_skipped = await _rows(
        factory, text, "SELECT region_id FROM wf.aqi_forecast_skips ORDER BY region_id"
    )
    assert regions_skipped == [(2,), (3,)]
