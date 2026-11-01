"""Regression tests for the 2026-11-01 production fixes."""

import math
from datetime import date, timedelta

import httpx
import pytest
import respx

from app.domain.features import (
    ROLLING_WINDOW_DAYS,
    WILDFIRE_V2_FEATURES,
    DailyWeatherRecord,
    compute_rolling_weather_features,
    extract_features,
)
from app.domain.fwi import fwi_inputs
from app.domain.names import humanize_gadm_name, normalize_name_key
from app.jobs.scheduler import job_lock_key
from app.ml.wildfire_predictor import missing_features, predict_wildfire_risk
from app.providers.open_meteo_air import OpenMeteoAirProvider
from app.providers.open_meteo_weather import OpenMeteoWeatherProvider

JOBS = [
    "ingest_fires",
    "ingest_weather",
    "update_fwi_state",
    "predict_risk",
    "ingest_air_quality",
    "forecast_aqi",
    "retention",
    "backfill_fires",
]


def test_every_job_has_its_own_lock():
    keys = [job_lock_key(j) for j in JOBS]
    assert len(set(keys)) == len(keys)
    assert all(0 <= k < 2**31 for k in keys)


def test_fwi_inputs_refuses_missing_values():
    assert fwi_inputs(30.0, None, 10.0, 0.0) is None
    assert fwi_inputs(30.0, 55.0, 10.0, 0.0) == {
        "temp": 30.0,
        "rh": 55.0,
        "wind": 10.0,
        "rain": 0.0,
    }


def test_rolling_features_without_history_are_nan_not_defaults():
    out = compute_rolling_weather_features([], date(2026, 11, 1))
    assert all(math.isnan(v) for v in out.values())


def _rec(d: date, precip: float = 0.0) -> DailyWeatherRecord:
    return DailyWeatherRecord(d, 32.0, 25.0, None, 50.0, 12.0, precip, None, None)


def test_rolling_window_is_capped_like_live_inference():
    today = date(2026, 11, 1)
    history = [_rec(today - timedelta(days=i)) for i in range(60, -1, -1)]  # 61 dry days
    out = compute_rolling_weather_features(history, today)
    assert out["consecutive_dry_days"] == ROLLING_WINDOW_DAYS


def test_extract_features_requires_real_fwi_values():
    today = date(2026, 11, 1)
    with pytest.raises(KeyError):
        extract_features(today, _rec(today), [_rec(today)], {}, 20.0, 75.0, {})


def test_v2_feature_set_is_fully_produced_by_live_feature_code():
    today = date(2026, 11, 1)
    history = [_rec(today - timedelta(days=i)) for i in range(30, -1, -1)]
    fwi = {"ffmc": 88.0, "dmc": 20.0, "dc": 60.0, "isi": 8.0, "bui": 25.0, "fwi": 12.0}
    feats = extract_features(today, history[-1], history, fwi, 20.9, 75.5, {}, 3, 10, 0.12)
    assert missing_features(feats, WILDFIRE_V2_FEATURES) == []


def test_predictor_falls_back_instead_of_zero_filling(tmp_path):
    # Artifact expects a feature the live dict does not have -> must NOT score with 0
    import hashlib
    import json

    import numpy as np
    import xgboost as xgb

    names = ["fwi", "brightness"]
    booster = xgb.train(
        {"objective": "binary:logistic"},
        xgb.DMatrix(np.array([[1.0, 300.0], [30.0, 340.0]]), label=[0, 1], feature_names=names),
        num_boost_round=2,
    )
    model_file = tmp_path / "toy_v1.json"
    booster.save_model(model_file)
    (tmp_path / "toy_v1_metadata.json").write_text(
        json.dumps(
            {"feature_list": names, "sha256": hashlib.sha256(model_file.read_bytes()).hexdigest()}
        )
    )
    from app.ml.loader import ModelLoader

    res = predict_wildfire_risk({"fwi": 22.0}, "toy_v1", ModelLoader(str(tmp_path)))
    assert res is not None and res.is_fallback is True and res.model_version == "fwi_fallback"


def test_predictor_returns_none_without_fwi():
    assert predict_wildfire_risk({"temp_max": 30.0}, "does_not_exist") is None


def test_gadm_names_are_humanized():
    assert humanize_gadm_name("NicobarIslands") == "Nicobar Islands"
    assert humanize_gadm_name("NorthandMiddleAndaman") == "North and Middle Andaman"
    assert humanize_gadm_name("DadraandNagarHaveli") == "Dadra and Nagar Haveli"
    assert humanize_gadm_name("NCTofDelhi") == "NCT of Delhi"
    assert humanize_gadm_name("Jalgaon") == "Jalgaon"
    assert humanize_gadm_name("Tamil Nadu") == "Tamil Nadu"
    assert normalize_name_key("Tamil Nadu") == normalize_name_key("TamilNadu")


@pytest.mark.asyncio
@respx.mock
async def test_weather_batch_keeps_missing_values_as_none():
    payload = [
        {
            "daily": {
                "time": ["2026-11-01"],
                "temperature_2m_max": [31.0],
                "relative_humidity_2m_mean": [60],
                "wind_speed_10m_max": [12.0],
                "precipitation_sum": [0.0],
            }
        },
        {
            "daily": {
                "time": ["2026-11-01"],
                "temperature_2m_max": [None],
                "relative_humidity_2m_mean": [70],
                "wind_speed_10m_max": [8.0],
                "precipitation_sum": [2.0],
            }
        },
    ]
    route = respx.get("https://api.open-meteo.com/v1/forecast").mock(
        return_value=httpx.Response(200, json=payload)
    )
    p = OpenMeteoWeatherProvider(forecast_url="https://api.open-meteo.com/v1/forecast")
    out = await p.fetch_weather_forecast_batch([(20.9, 75.5), (21.1, 79.0)])
    assert route.call_count == 1  # one HTTP call for both districts
    assert out[0][0].temp_max == 31.0
    assert out[1][0].temp_max is None  # never replaced with a default
    assert out[0][0].soil_moisture is None


@pytest.mark.asyncio
@respx.mock
async def test_aq_batch_one_request_for_many_points():
    payload = [
        {"current": {"time": "2026-11-01T05:00", "pm2_5": 40.0, "pm10": 80.0}},
        {"current": {"time": "2026-11-01T05:00", "pm2_5": 10.0, "pm10": 20.0}},
    ]
    route = respx.get("https://air-quality-api.open-meteo.com/v1/air-quality").mock(
        return_value=httpx.Response(200, json=payload)
    )
    p = OpenMeteoAirProvider(air_url="https://air-quality-api.open-meteo.com/v1/air-quality")
    out = await p.fetch_air_quality_batch([(20.9, 75.5), (21.1, 79.0)])
    assert route.call_count == 1
    assert out[0][0].pm25 == 40.0 and out[1][0].pm25 == 10.0


def test_models_comparison_reads_real_evaluation():
    from fastapi.testclient import TestClient

    from app.main import app

    data = TestClient(app).get("/api/v1/models/comparison").json()
    assert data["status"] == "available"
    names = {m["name"] for m in data["models"]}
    assert {"xgboost", "fwi_only", "climatology", "persistence_fires_prev_7d"} <= names
    test = data["wildfire_comparison"]["test"]
    assert test["xgboost"]["roc_auc"] > test["climatology"]["roc_auc"]


def test_firms_window_url_has_start_date():
    import asyncio
    from datetime import date

    import httpx

    from app.providers.firms import FirmsProvider

    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(200, text="latitude,longitude,acq_date,acq_time\n10,77,,\n")

    async def run() -> list:
        prov = FirmsProvider(map_key="KEY", sources=["VIIRS_NOAA20_NRT"])
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            text = await prov._fetch_source_csv(
                client, "VIIRS_NOAA20_NRT", [68, 6, 97, 37], 5, date(2026, 10, 1)
            )
        return prov.parse_firms_csv(text, "VIIRS_NOAA20_NRT")

    rows = asyncio.run(run())
    assert seen[0].endswith("/68,6,97,37/5/2026-10-01")
    assert rows == []  # rows without a timestamp are dropped, never given a fake date


def test_open_meteo_quota_handling(monkeypatch):
    import asyncio

    import httpx
    import pytest

    from app.providers import open_meteo_http as om

    replies = iter(
        [
            httpx.Response(429, text='{"reason":"Minutely API request limit exceeded"}'),
            httpx.Response(200, json={"ok": 1}),
        ]
    )
    real_client = httpx.AsyncClient

    def fake_client(*a, **k):
        k["transport"] = httpx.MockTransport(lambda req: next(replies))
        return real_client(*a, **k)

    async def no_sleep(_):
        return None

    monkeypatch.setattr(om.httpx, "AsyncClient", fake_client)
    monkeypatch.setattr(om.asyncio, "sleep", no_sleep)
    assert asyncio.run(om.get_json("https://x.test", {})) == {"ok": 1}

    replies = iter([httpx.Response(429, text='{"reason":"Hourly API request limit exceeded"}')])
    with pytest.raises(om.OpenMeteoQuotaExceeded):
        asyncio.run(om.get_json("https://x.test", {}))
