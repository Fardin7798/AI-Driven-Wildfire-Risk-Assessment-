"""AQI model B serving: loader checksums, request formatting, skip rules, and offline parity of
the serving feature path with the v3 training dataset (skipped when raw data is absent)."""

import json
import os
import shutil
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pytest

pd = pytest.importorskip("pandas")

from app.domain.aqi_features import HISTORY_DAYS, POLLUTANTS, WEATHER_DAILY  # noqa: E402
from app.ml import aqi_station_b as sb  # noqa: E402
from app.ml.loader import ModelLoader  # noqa: E402

BACKEND = Path(__file__).resolve().parents[2]
REPO = BACKEND.parent
MODEL_DIR = BACKEND / "models"
VERSION = "aqi_station_xgb_v3"
DATASET = REPO / "data" / "processed" / "aqi_station" / "aqi_station_dataset.parquet"
CAMS_DIR = REPO / "data" / "raw" / "cams"
WEATHER_DIR = REPO / "data" / "raw" / "openmeteo_weather"


@pytest.fixture(scope="module")
def model():
    m = ModelLoader(str(MODEL_DIR)).load_aqi_model(VERSION)
    assert m is not None
    return m


# ---------------------------------------------------------------- loader
def test_loader_verifies_all_boosters(model):
    assert model.model_version == VERSION
    assert len(model.feature_list) == 43
    assert set(model.boosters) == {1, 2, 3}
    for h, b in model.boosters.items():
        assert b.num_boosted_rounds() == model.metadata["models"][f"no_station_h{h}"]["n_trees"]
        assert list(b.feature_names) == model.feature_list


def test_loader_rejects_tampered_booster(tmp_path):
    shutil.copytree(MODEL_DIR / VERSION, tmp_path / VERSION)
    with open(tmp_path / VERSION / "aqi_station_no_station_h2.json", "a") as f:
        f.write(" ")
    assert ModelLoader(str(tmp_path)).load_aqi_model(VERSION) is None


def test_loader_missing_artifact(tmp_path):
    assert ModelLoader(str(tmp_path)).load_aqi_model(VERSION) is None


# ---------------------------------------------------------------- requests
def test_origin_is_yesterday_ist():
    # 2026-11-03 00:30 IST is still 2026-11-02 in UTC
    now = datetime.fromisoformat("2026-11-02T19:00:00+00:00")
    assert sb.origin_day(now) == date(2026, 11, 2)


def test_request_params_match_training_downloads():
    assert sb.format_coord(92.665) == "92.665"
    assert sb.format_coord(28.65381) == "28.6538"
    p = sb.cams_params(7.5254, 93.5992, date(2026, 11, 2))
    assert p["latitude"] == "7.5254" and p["longitude"] == "93.5992"
    assert p["hourly"] == ",".join(POLLUTANTS)
    assert p["start_date"] == "2026-10-20" and p["end_date"] == "2026-11-02"
    assert p["timezone"] == "Asia/Kolkata"
    w = sb.weather_params(7.5254, 93.5992)
    assert w["daily"] == ",".join(WEATHER_DAILY) and w["past_days"] == 2
    assert w["timezone"] == "Asia/Kolkata"


# ---------------------------------------------------------------- features / skip
def _payloads(origin: date, pm25: float = 50.0, hours_missing_on_origin: int = 0):
    first = origin - timedelta(days=HISTORY_DAYS)
    times = pd.date_range(str(first), periods=24 * (HISTORY_DAYS + 1), freq="h")
    base = {"pm2_5": pm25, "pm10": 80.0, "nitrogen_dioxide": 20.0}
    base |= {"sulphur_dioxide": 10.0, "carbon_monoxide": 800.0, "ozone": 40.0}
    hourly: dict = {"time": list(times.strftime("%Y-%m-%dT%H:%M"))}
    for k, v in base.items():
        col = [v] * len(times)
        for i in range(hours_missing_on_origin):
            col[-1 - i] = None
        hourly[k] = col
    days = [str(origin - timedelta(days=d)) for d in (2, 1, 0)] + [str(origin + timedelta(1))]
    daily: dict = {"time": days}
    for om in WEATHER_DAILY:
        daily[om] = [20.0, 21.0, 22.0, 23.0]
    return hourly, daily


def test_build_features_complete_row(model):
    origin = date(2026, 11, 2)
    hourly, daily = _payloads(origin)
    row = sb.build_features(1, 7.5254, 93.5992, origin, hourly, daily)
    assert sb.missing_features(row, model.feature_list) == []
    assert row["cams_pm25_lag0"] == 50.0 and row["temp_max"] == 22.0
    assert row["temp_max_lag1"] == 21.0 and row["lat"] == 7.5254
    out = sb.predict(model, row, origin)
    assert [f["target_date"] for f in out] == ["2026-11-03", "2026-11-04", "2026-11-05"]
    assert all(0 <= f["pm25_si_pred"] <= 500 for f in out)


def test_short_cams_day_is_missing_not_filled(model):
    origin = date(2026, 11, 2)
    hourly, daily = _payloads(origin, hours_missing_on_origin=9)  # 15 valid hours < 16
    row = sb.build_features(1, 7.5254, 93.5992, origin, hourly, daily)
    missing = sb.missing_features(row, model.feature_list)
    assert "cams_pm25_lag0" in missing and "cams_pm25_si_lag0" in missing


async def test_forecast_district_skips_with_reason(model, monkeypatch):
    origin = date(2026, 11, 2)
    hourly, daily = _payloads(origin, hours_missing_on_origin=9)

    async def fake_get_json(url, params):
        return {"hourly": hourly} if "hourly" in params else {"daily": daily}

    monkeypatch.setattr(sb, "get_json", fake_get_json)
    res = await sb.forecast_district(1, 7.5254, 93.5992, model=model, origin=origin)
    assert res["status"] == "skipped" and res["forecasts"] == []
    assert "cams_pm25_lag0" in res["reason"]

    hourly, daily = _payloads(origin)
    res = await sb.forecast_district(1, 7.5254, 93.5992, model=model, origin=origin)
    assert res["status"] == "ok" and res["extrapolated"] is True
    assert all(f["extrapolated"] is True for f in res["forecasts"])

    res = await sb.forecast_district(1, 7.6, 93.5992, model=model, origin=origin)
    assert res["status"] == "skipped" and "training centroid" in res["reason"]


def test_predictions_clipped(model):
    origin = date(2026, 11, 2)
    hourly, daily = _payloads(origin, pm25=900.0)
    row = sb.build_features(1, 7.5254, 93.5992, origin, hourly, daily)
    assert all(0 <= f["aqi_pred"] <= 500 for f in sb.predict(model, row, origin))


# ---------------------------------------------------------------- offline parity
# Every origin of the dataset through the serving path takes ~30 min; pytest checks every
# PARITY_STEP-th origin of each district (WF_PARITY_STEP=1 checks all).
PARITY_STEP = int(os.environ.get("WF_PARITY_STEP", "40"))


def _as_payload(df: "pd.DataFrame") -> dict:
    """CSV frame -> Open-Meteo JSON block (empty cells as null)."""
    return {c: [None if pd.isna(v) else v for v in df[c].tolist()] for c in df.columns}


def district_parity(model, rid: int, part: "pd.DataFrame", step: int) -> dict:
    """Raw CAMS/weather CSVs of one district -> serving feature rows (windowed exactly as live:
    t-HISTORY_DAYS..t of CAMS, t-1..t+1 of weather) vs the dataset rows of that district."""
    feats = model.feature_list
    cov = {d["region_id"]: d for d in model.coverage["districts"]}[rid]
    cams = pd.read_csv(CAMS_DIR / f"{rid}.csv.gz")
    cams_day = pd.to_datetime(cams["time"]).dt.date.to_numpy()
    wx = pd.read_csv(WEATHER_DIR / f"{rid}.csv")
    wx_day = pd.to_datetime(wx["date"]).dt.date.to_numpy()
    wx = wx.rename(columns={v: k for k, v in WEATHER_DAILY.items()} | {"date": "time"})
    part = part.sort_values("date").iloc[::step]
    n, max_diff, nan_mismatch = 0, 0.0, 0
    for r in part.itertuples(index=False):
        t = r.date
        h = cams[(cams_day >= t - timedelta(days=HISTORY_DAYS)) & (cams_day <= t)]
        w = wx[(wx_day >= t - timedelta(days=1)) & (wx_day <= t + timedelta(days=1))]
        row = sb.build_features(rid, cov["lat"], cov["lon"], t, _as_payload(h), _as_payload(w))
        live = row[feats].to_numpy(dtype=float)
        train = np.asarray([getattr(r, f) for f in feats], dtype=float)
        nan_mismatch += int((np.isnan(live) != np.isnan(train)).sum())
        both = ~np.isnan(live) & ~np.isnan(train)
        if both.any():
            max_diff = max(max_diff, float(np.abs(live[both] - train[both]).max()))
        n += 1
    return {"rows": n, "max_abs_diff": max_diff, "nan_mismatch": nan_mismatch}


def parity_reference(model) -> "pd.DataFrame":
    ds = pd.read_parquet(DATASET, columns=["region_id", "date", *model.feature_list])
    return ds.drop_duplicates(["region_id", "date"])


@pytest.mark.skipif(
    not (DATASET.exists() and CAMS_DIR.exists() and WEATHER_DIR.exists()),
    reason="raw CAMS/weather files or v3 dataset not present",
)
def test_offline_parity_with_v3_dataset(model):
    pytest.importorskip("pyarrow")
    ref = parity_reference(model)
    res = [district_parity(model, int(rid), p, PARITY_STEP) for rid, p in ref.groupby("region_id")]
    total = {
        "districts": len(res),
        "rows": sum(r["rows"] for r in res),
        "max_abs_diff": max(r["max_abs_diff"] for r in res),
        "nan_mismatch": sum(r["nan_mismatch"] for r in res),
    }
    print(json.dumps(total))
    assert total["districts"] == ref["region_id"].nunique()
    assert total["nan_mismatch"] == 0
    assert total["max_abs_diff"] == 0.0
