"""PM2.5 sub-index target, 16-hour rule, invalid hours and no-leakage lags of
ml/pipeline/build_aqi_dataset.py, plus the station QC rules of validate_cams_openaq.py."""

import sys
from datetime import date
from pathlib import Path

import numpy as np
import pytest

pd = pytest.importorskip("pandas")

PIPELINE = Path(__file__).resolve().parents[3] / "ml" / "pipeline"
sys.path.insert(0, str(PIPELINE))
import build_aqi_dataset as b  # noqa: E402

from app.domain.aqi import calculate_sub_index  # noqa: E402

POLS = ["pm25", "pm10", "no2", "so2", "co", "o3"]


def _hourly(days: int, start: str = "2024-01-01", **const: float) -> "pd.DataFrame":
    idx = pd.date_range(start, periods=24 * days, freq="h")
    base = {"pm25": 50.0, "pm10": 80.0, "no2": 20.0, "so2": 10.0, "co": 800.0, "o3": 40.0}
    base.update(const)
    return pd.DataFrame({p: np.full(len(idx), base[p]) for p in POLS}, index=idx)


def _cams_file(tmp_path: Path, h: "pd.DataFrame") -> Path:
    inv = {v: k for k, v in b.POLLUTANTS.items()}
    df = h.rename(columns=inv)
    df.insert(0, "time", h.index.strftime("%Y-%m-%dT%H:%M"))
    f = tmp_path / "1.csv.gz"
    df.to_csv(f, index=False)
    return f


def test_target_is_pm25_sub_index_only():
    # O3/PM10/CO far above PM2.5's sub-index must not change the target
    h = _hourly(1, pm25=75.0, o3=500.0, pm10=550.0, co=30000.0)
    d = b.daily_table(h).iloc[0]
    assert d["pm25_si"] == calculate_sub_index("pm25", 75.0) == 149
    assert "aqi" not in b.daily_table(h).columns
    assert all(t.startswith("pm25_si_t+") for t in b.TARGETS)


def test_pm25_sub_index_uses_24h_mean():
    h = _hourly(1)
    v = np.full(24, 20.0)
    v[:12] = 100.0
    h["pm25"] = v
    d = b.daily_table(h).iloc[0]
    assert d["pm25_mean"] == pytest.approx(60.0)
    assert d["pm25_si"] == calculate_sub_index("pm25", 60.0)


def test_16_hour_minimum_per_pollutant():
    h = _hourly(2)
    h.iloc[:9, h.columns.get_loc("pm25")] = np.nan  # day 1: 15 valid hours
    h.iloc[24:32, h.columns.get_loc("pm25")] = np.nan  # day 2: 16 valid hours
    d = b.daily_table(h)
    assert np.isnan(d["pm25_mean"].iloc[0])
    assert np.isnan(d["pm25_si"].iloc[0])  # no fallback to other pollutants
    assert d["pm25_mean"].iloc[1] == pytest.approx(50.0)


def test_missing_hour_rows_count_as_missing():
    h = _hourly(1).iloc[:15]  # only 15 hourly rows exist for the day
    d = b.daily_table(h)
    assert np.isnan(d["pm25_si"].iloc[0])
    assert np.isnan(d["pm10_mean"].iloc[0])


def test_read_cams_invalidates_negatives_and_pm10_ceiling(tmp_path):
    h = _hourly(1)
    h.iloc[:9, h.columns.get_loc("pm25")] = -1.0  # 15 valid hours left -> day missing
    h.iloc[:9, h.columns.get_loc("pm10")] = b.CAMS_PM10_CEILING
    clean, counts = b.read_cams(_cams_file(tmp_path, h))
    assert counts == {"negative": 9, "pm10_ceiling": 9}
    assert clean["pm25"].isna().sum() == 9 and clean["pm10"].isna().sum() == 9
    d = b.daily_table(clean).iloc[0]
    assert np.isnan(d["pm25_si"]) and np.isnan(d["pm10_mean"])
    assert d["o3_mean"] == pytest.approx(40.0)


def _panel(si: list[float]) -> "pd.DataFrame":
    n = len(si)
    dates = pd.date_range("2024-01-01", periods=n, freq="D").date
    p = pd.DataFrame({"region_id": 1, "date": dates, "pm25_si": si, "lat": 20.0, "lon": 75.0})
    for pol in POLS:
        p[f"{pol}_mean"] = np.arange(n, dtype=float)
    for w in b.WEATHER:
        p[w] = np.arange(n, dtype=float)
    return p


def test_lags_and_targets_and_no_leakage():
    si = [float(100 + i) for i in range(20)]
    f = b.add_features(_panel(si))
    t = 15
    row = f.iloc[t]
    for k in range(7):
        assert row[f"pm25_si_lag{k}"] == si[t - k]
    for h in (1, 2, 3):
        assert row[f"pm25_si_t+{h}"] == si[t + h]
    assert row["pm25_si_roll7"] == pytest.approx(np.mean(si[t - 6 : t + 1]))
    assert row["pm25_si_roll14"] == pytest.approx(np.mean(si[t - 13 : t + 1]))
    assert row["pm25_lag0"] == t and row["pm10_lag2"] == t - 2
    assert row["temp_max"] == t and row["temp_max_lag1"] == t - 1
    assert np.isnan(f.iloc[5]["pm25_si_roll7"])  # incomplete window is missing, not partial

    # Changing every value after day t must not change any feature at t
    future = list(si)
    for i in range(t + 1, len(future)):
        future[i] = 999.0
    p2 = _panel(future)
    p2.loc[t + 1 :, [f"{x}_mean" for x in POLS] + b.WEATHER] = -5.0
    f2 = b.add_features(p2)
    cols = b.feature_columns()
    pd.testing.assert_series_equal(f.iloc[t][cols], f2.iloc[t][cols], check_names=False)
    assert not set(cols) & set(b.TARGETS)


def test_missing_day_is_missing_lag_not_previous_row():
    si = [float(100 + i) for i in range(10)]
    si[4] = np.nan
    f = b.add_features(_panel(si))
    assert np.isnan(f.iloc[5]["pm25_si_lag1"])
    assert f.iloc[5]["pm25_si_lag2"] == si[3]


def test_regions_do_not_bleed_into_each_other():
    a = _panel([100.0] * 10)
    c = _panel([300.0] * 10)
    c["region_id"] = 2
    f = b.add_features(pd.concat([a, c], ignore_index=True))
    first_b = f[f["region_id"] == 2].iloc[0]
    assert np.isnan(first_b["pm25_si_lag1"])
    last_a = f[f["region_id"] == 1].iloc[-1]
    assert np.isnan(last_a["pm25_si_t+1"])


def test_split_boundaries():
    s = b.assign_split(
        pd.Series([date(2024, 10, 31), date(2024, 11, 1), date(2025, 11, 1), date(2026, 10, 29)])
    )
    assert list(s.iloc[:3]) == ["train", "val", "test"]
    assert pd.isna(s.iloc[3])


def test_baselines_persistence_and_seasonal_naive():
    si = [float(10 * i) for i in range(30)]
    f = b.add_features(_panel(si)).dropna(subset=b.feature_columns() + b.TARGETS).copy()
    f["split"] = "test"
    res = b.baselines(f)
    # linear series: persistence error = 10*h, seasonal-naive error = 70 for every h
    for h in (1, 2, 3):
        assert res["test"]["persistence"][f"h{h}"]["mae"] == pytest.approx(10.0 * h)
        assert res["test"]["seasonal_naive"][f"h{h}"]["mae"] == pytest.approx(70.0)


def test_station_exclusion_rules():
    validate = pytest.importorskip("validate_cams_openaq")
    d = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=10, freq="D").strftime("%Y-%m-%d"),
            "value": [10.0, 0.0, 985.0, 1200.0, 984.0, 7.0, 7.0, 7.0, 7.0, 7.0],
            "pct_complete": [80.0, 80.0, 80.0, 80.0, 74.0, 90.0, 90.0, 90.0, 90.0, 90.0],
        }
    )
    m = validate.station_exclusions(d)
    drop = pd.concat(m, axis=1).any(axis=1)
    assert list(drop) == [False, True, True, True, True, True, True, True, True, True]
    assert m["stuck_run_ge_5"].sum() == 5
    assert validate.STATION_CEILING == 985.0


def test_forecasts_scored_on_target_day():
    validate = pytest.importorskip("validate_cams_openaq")
    pairs = pd.DataFrame(
        {
            "sensor_id": [1, 1, 1],
            "region_id": [7, 7, 7],
            "date": [date(2025, 11, 2), date(2025, 11, 3), date(2025, 11, 4)],
            "station_si": [100.0, 110.0, 120.0],
        }
    )
    preds = pd.DataFrame(
        {
            "region_id": [7, 7, 7],
            "horizon": [1, 1, 1],
            "target_date": [date(2025, 11, 2), date(2025, 11, 3), date(2025, 11, 5)],
            "model": [105.0, 115.0, 0.0],
            "persistence": [90.0, 100.0, 0.0],
            "seasonal_naive": [100.0, 110.0, 0.0],
            "target": [100.0, 110.0, 0.0],
        }
    )
    r = validate.forecasts_vs_station(pairs, preds)["h1"]
    assert r["model"]["n_pairs"] == 2  # 2025-11-05 has no station day
    assert r["model"]["bias"] == pytest.approx(5.0)
    assert r["persistence"]["mae"] == pytest.approx(10.0)
    assert r["target"]["mae"] == pytest.approx(0.0)
