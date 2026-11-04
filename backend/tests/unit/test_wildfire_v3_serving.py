"""wildfire_xgb_v3 serving: ECMWF IFS weather derivation, artifact loading, API endpoints."""

import json
import shutil
from datetime import date
from pathlib import Path

import httpx
import pytest
import respx

from app.core.config import settings
from app.domain.features import WILDFIRE_V2_FEATURES
from app.ml.loader import ModelLoader
from app.providers.open_meteo_weather import (
    DAILY_VARIABLES,
    PROVIDER_HISTORICAL,
    OpenMeteoWeatherProvider,
    hourly_temperature_extremes,
    parse_payload,
)

BACKEND = Path(__file__).resolve().parents[2]
MODEL_DIR = BACKEND / "models"
VERSION = "wildfire_xgb_v3"
FIXTURE = BACKEND / "tests" / "fixtures" / "ifs_parity_20261025_20261101.json"


def _hours(day: str, temps: list[float | None]) -> dict:
    return {"time": [f"{day}T{h:02d}:00" for h in range(len(temps))], "temperature_2m": temps}


def test_tmax_tmin_come_from_24_hourly_values():
    temps = [20.0 + h * 0.5 for h in range(24)]
    out = hourly_temperature_extremes(_hours("2026-11-01", temps))
    assert out[date(2026, 11, 1)] == (31.5, 20.0)


def test_day_with_missing_or_null_hour_is_none():
    short = hourly_temperature_extremes(_hours("2026-11-01", [25.0] * 23))
    assert short[date(2026, 11, 1)] == (None, None)
    temps: list[float | None] = [25.0] * 24
    temps[5] = None
    with_null = hourly_temperature_extremes(_hours("2026-11-01", temps))
    assert with_null[date(2026, 11, 1)] == (None, None)


def test_native_daily_tmax_is_ignored_and_missing_stays_missing():
    payload = {
        "daily": {
            "time": ["2026-11-01", "2026-11-02"],
            "temperature_2m_max": [99.0, 99.0],  # must never be used
            "temperature_2m_mean": [25.0, None],
            "relative_humidity_2m_mean": [60, 61],
            "wind_speed_10m_max": [12.0, 11.0],
            "precipitation_sum": [0.0, 0.2],
        },
        "hourly": {
            "time": [f"2026-11-01T{h:02d}:00" for h in range(24)]
            + [f"2026-11-02T{h:02d}:00" for h in range(24)],
            "temperature_2m": [20.0 + h for h in range(24)] + [None] + [21.0] * 23,
        },
    }
    recs = parse_payload(payload, PROVIDER_HISTORICAL)
    assert (recs[0].temp_max, recs[0].temp_min) == (43.0, 20.0)
    assert recs[1].temp_max is None and recs[1].temp_min is None
    assert recs[1].temp_mean is None  # absent value is not filled
    assert recs[0].et0 is None and recs[0].soil_moisture is None


@pytest.mark.asyncio
@respx.mock
async def test_forecast_request_pins_ecmwf_ifs_and_hourly_temperature():
    route = respx.get(settings.OPEN_METEO_WEATHER_URL).mock(
        return_value=httpx.Response(
            200,
            json=[
                {"daily": {"time": []}, "hourly": {"time": []}},
                {"daily": {"time": []}, "hourly": {"time": []}},
            ],
        )
    )
    await OpenMeteoWeatherProvider().fetch_weather_forecast_batch([(20.9, 75.5), (21.1, 79.0)])
    assert route.call_count == 1  # one HTTP call for both districts
    q = route.calls[0].request.url.params
    assert q["models"] == "ecmwf_ifs"
    assert q["timezone"] == "Asia/Kolkata"
    assert q["hourly"] == "temperature_2m"
    assert "temperature_2m_max" not in q["daily"] and "temperature_2m_min" not in q["daily"]
    assert q["daily"].split(",") == DAILY_VARIABLES
    assert q["latitude"] == "20.9000,21.1000"


@pytest.mark.asyncio
@respx.mock
async def test_historical_uses_historical_forecast_api_not_era5():
    assert "historical-forecast-api" in settings.OPEN_METEO_HISTORICAL_FORECAST_URL
    route = respx.get(settings.OPEN_METEO_HISTORICAL_FORECAST_URL).mock(
        return_value=httpx.Response(200, json={"daily": {"time": []}, "hourly": {"time": []}})
    )
    await OpenMeteoWeatherProvider().fetch_historical_weather(
        20.9, 75.5, date(2026, 10, 1), date(2026, 10, 31)
    )
    q = route.calls[0].request.url.params
    assert q["models"] == "ecmwf_ifs"
    assert (q["start_date"], q["end_date"]) == ("2026-10-01", "2026-10-31")


@pytest.mark.asyncio
@respx.mock
async def test_recorded_api_response_matches_training_ifs_extraction():
    """Recorded Historical Forecast API response (3 districts, 2026-10-25..11-01) parsed by the
    serving code equals the training extraction within API rounding (0.1 C / 1 % / 0.1 km/h)."""
    fx = json.loads(FIXTURE.read_text(encoding="utf-8"))
    respx.get(settings.OPEN_METEO_HISTORICAL_FORECAST_URL).mock(
        return_value=httpx.Response(200, json=fx["response"])
    )
    params = fx["request_params"]
    coords = list(
        zip(
            map(float, params["latitude"].split(",")),
            map(float, params["longitude"].split(",")),
            strict=True,
        )
    )
    out = await OpenMeteoWeatherProvider().fetch_historical_weather_batch(
        coords, date(2026, 10, 25), date(2026, 11, 1)
    )
    tol = {
        "temp_max": 0.051,
        "temp_min": 0.051,
        "temp_mean": 0.051,
        "rh_mean": 0.5,
        "wind_max": 0.051,
        "precip_sum": 0.051,
    }
    for rid, recs in zip(fx["region_ids"], out, strict=True):
        exp = fx["expected"][str(rid)]
        assert [r.record_date.isoformat() for r in recs] == exp["date"]
        for var, t in tol.items():
            for r, e in zip(recs, exp[var], strict=True):
                v = getattr(r, var)
                assert v is not None and abs(v - e) <= t, (rid, var, r.record_date, v, e)


def test_v3_artifact_loads_and_is_active():
    assert settings.ACTIVE_WILDFIRE_MODEL == VERSION
    art = ModelLoader(str(MODEL_DIR)).load_wildfire_model()
    assert art is not None and art.model_obj is not None and not art.is_fallback
    assert art.model_version == VERSION
    assert art.feature_list == WILDFIRE_V2_FEATURES
    ev = json.loads(
        (MODEL_DIR / VERSION / f"{VERSION}_evaluation.json").read_text(encoding="utf-8")
    )
    assert art.thresholds == ev["thresholds_from_validation"]
    assert art.thresholds == {"moderate": 0.143, "high": 0.3256, "extreme": 0.5574}
    assert art.metrics["test_year"] == 2025 and art.metrics["roc_auc"] == 0.9232
    clim = art.metadata["climatology"]
    assert clim["train_years"] == [2019, 2020, 2021, 2022, 2023]
    assert len(clim["monthly_rate"]) == 676
    assert all(len(v) == 12 for v in clim["monthly_rate"].values())
    assert "test_disclosure" in art.metadata


def test_v2_artifacts_are_gone():
    assert not list(MODEL_DIR.glob("wildfire_xgb_v2*"))


def test_loader_rejects_tampered_booster(tmp_path):
    shutil.copytree(MODEL_DIR / VERSION, tmp_path / VERSION)
    booster = tmp_path / VERSION / f"{VERSION}.json"
    booster.write_bytes(booster.read_bytes() + b" ")
    assert ModelLoader(str(tmp_path)).load_wildfire_model(VERSION) is None


def test_loader_rejects_version_mismatch(tmp_path):
    shutil.copytree(MODEL_DIR / VERSION, tmp_path / "other_v9")
    for f in (tmp_path / "other_v9").iterdir():
        f.rename(f.with_name(f.name.replace(VERSION, "other_v9")))
    assert ModelLoader(str(tmp_path)).load_wildfire_model("other_v9") is None


def test_models_endpoints_report_v3():
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    cur = client.get("/api/v1/models/current").json()
    wf = next(m for m in cur if m["model_type"] == "wildfire")
    assert wf["version"] == VERSION and wf["status"] == "active"
    assert wf["thresholds"]["high"] == 0.3256
    assert "smoke run" in wf["metrics"]["test_disclosure"]
    comp = client.get("/api/v1/models/comparison").json()
    assert comp["status"] == "available"
    assert comp["wildfire_comparison"]["model"] == VERSION
    test = comp["wildfire_comparison"]["test"]
    assert test["xgboost"]["roc_auc"] == 0.9232
    assert test["climatology"]["roc_auc"] == 0.8889


def test_serving_feature_vector_equals_dataset_builder():
    """Same district weather series -> predict_risk/update_fwi_state path and the training
    builder (ml/pipeline/build_wildfire_dataset.build_district) give identical features."""
    import math
    import sys
    from datetime import timedelta

    pd = pytest.importorskip("pandas")
    pytest.importorskip("geopandas")
    sys.path.insert(0, str(BACKEND.parent / "ml" / "pipeline"))
    import build_wildfire_dataset as builder

    from app.db.models.weather import WeatherDaily
    from app.domain.features import extract_features
    from app.domain.fwi import FWI_STARTUP, calculate_daily_fwi, fwi_inputs
    from app.jobs.predict_risk import _to_record, missing_window_dates

    start, target = date(2026, 8, 1), date(2026, 11, 1)
    days = [start + timedelta(days=i) for i in range((target - start).days + 1)]
    rows = [
        WeatherDaily(
            region_id=360,
            date=d,
            is_forecast=False,
            temp_max=round(31 + 4 * math.sin(i / 5), 1),
            temp_min=round(21 + 2 * math.sin(i / 7), 1),
            temp_mean=round(26 + 3 * math.sin(i / 5), 1),
            rh_mean=float(55 + (i * 7) % 30),
            rh_min=None,
            wind_max=round(8 + (i * 3) % 11 * 0.9, 1),
            precip_sum=float([0, 0, 0.4, 0, 12.5, 0, 1.2][i % 7]),
            et0=None,
            soil_moisture=None,
        )
        for i, d in enumerate(days)
    ]
    state = None
    fwi_today = None
    for r in rows:  # update_fwi_state: yesterday's state, else start-up codes
        inputs = fwi_inputs(r.temp_max, r.rh_mean, r.wind_max, r.precip_sum)
        assert inputs is not None
        prev = state or FWI_STARTUP
        fwi_today = calculate_daily_fwi(
            month=r.date.month,
            prev_ffmc=prev["ffmc"],
            prev_dmc=prev["dmc"],
            prev_dc=prev["dc"],
            **inputs,
        )
        state = {"ffmc": fwi_today.ffmc, "dmc": fwi_today.dmc, "dc": fwi_today.dc}
    per_day = {r.date: _to_record(r) for r in rows if r.date >= target - timedelta(days=30)}
    assert not missing_window_dates(set(per_day), target)
    clim = [0.01 * m for m in range(12)]
    serving = extract_features(
        target_date=target,
        current_weather=per_day[target],
        weather_history=[per_day[d] for d in sorted(per_day)],
        fwi_values={k: getattr(fwi_today, k) for k in ("ffmc", "dmc", "dc", "isi", "bui", "fwi")},
        lat=20.9375,
        lon=75.4913,
        landcover={},
        fires_prev_7d=3,
        fires_prev_30d=11,
        climatological_fire_freq=clim[target.month - 1],
    )
    weather = pd.DataFrame(
        [
            {
                "gadm_id": "IND.20.13_1",
                "date": r.date,
                "temp_max": r.temp_max,
                "temp_mean": r.temp_mean,
                "rh_mean": r.rh_mean,
                "wind_max": r.wind_max,
                "precip_sum": r.precip_sum,
            }
            for r in rows
        ]
    )
    det = {target - timedelta(days=2): 3, target - timedelta(days=20): 8}
    built = builder.build_district("IND.20.13_1", 20.9375, 75.4913, weather, det, {}, clim, target)[
        0
    ]
    assert {k: serving[k] for k in WILDFIRE_V2_FEATURES} == {
        k: built[k] for k in WILDFIRE_V2_FEATURES
    }
