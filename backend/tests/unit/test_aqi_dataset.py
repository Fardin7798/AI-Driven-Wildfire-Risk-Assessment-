"""Daily CPCB aggregation, 16-hour rule and no-leakage lags of ml/pipeline/build_aqi_dataset.py."""

import sys
from datetime import date
from pathlib import Path

import numpy as np
import pytest

pd = pytest.importorskip("pandas")

PIPELINE = Path(__file__).resolve().parents[3] / "ml" / "pipeline"
sys.path.insert(0, str(PIPELINE))
import build_aqi_dataset as b  # noqa: E402

from app.domain.aqi import calculate_cpcb_aqi  # noqa: E402

POLS = ["pm25", "pm10", "no2", "so2", "co", "o3"]


def _hourly(days: int, start: str = "2024-01-01", **const: float) -> "pd.DataFrame":
    idx = pd.date_range(start, periods=24 * days, freq="h")
    base = {"pm25": 50.0, "pm10": 80.0, "no2": 20.0, "so2": 10.0, "co": 800.0, "o3": 40.0}
    base.update(const)
    return pd.DataFrame({p: np.full(len(idx), base[p]) for p in POLS}, index=idx)


def test_daily_aqi_matches_production_function_with_co_in_mg():
    d = b.daily_table(_hourly(1, co=1500.0)).iloc[0]
    expected = calculate_cpcb_aqi(
        {"pm25": 50.0, "pm10": 80.0, "no2": 20.0, "so2": 10.0, "co": 1.5, "o3": 40.0}
    )
    assert expected is not None
    assert d["aqi"] == expected.aqi
    assert d["co_8h"] == pytest.approx(1500.0)


def test_16_hour_minimum_per_pollutant():
    h = _hourly(2)
    h.iloc[:9, h.columns.get_loc("pm25")] = np.nan  # day 1: 15 valid hours
    h.iloc[24:32, h.columns.get_loc("pm25")] = np.nan  # day 2: 16 valid hours
    d = b.daily_table(h)
    assert np.isnan(d["pm25_mean"].iloc[0])
    assert d["pm25_mean"].iloc[1] == pytest.approx(50.0)
    # PM10 still present, so day 1 AQI is valid without PM2.5
    assert not np.isnan(d["aqi"].iloc[0])


def test_missing_hour_rows_count_as_missing_and_negatives_invalid():
    h = _hourly(1).iloc[:15]  # only 15 hourly rows exist for the day
    assert np.isnan(b.daily_table(h)["pm10_mean"].iloc[0])
    h = _hourly(1)
    h.iloc[:9, h.columns.get_loc("o3")] = -1.0
    assert np.isnan(b.daily_table(h)["o3_8h"].iloc[0])


def test_aqi_none_without_pm_is_nan():
    h = _hourly(1)
    h[["pm25", "pm10"]] = np.nan
    assert np.isnan(b.daily_table(h)["aqi"].iloc[0])


def test_o3_uses_max_within_day_8h_mean():
    h = _hourly(1)
    o3 = np.full(24, 40.0)
    o3[10:18] = 120.0  # one full 8-h window at 120
    h["o3"] = o3
    assert b.daily_table(h)["o3_8h"].iloc[0] == pytest.approx(120.0)
    # 24-h mean is the plain mean
    assert b.daily_table(h)["o3_mean"].iloc[0] == pytest.approx((16 * 40 + 8 * 120) / 24)


def _panel(aqi: list[float]) -> "pd.DataFrame":
    n = len(aqi)
    dates = pd.date_range("2024-01-01", periods=n, freq="D").date
    p = pd.DataFrame({"region_id": 1, "date": dates, "aqi": aqi, "lat": 20.0, "lon": 75.0})
    for pol in POLS:
        p[f"{pol}_mean"] = np.arange(n, dtype=float)
    for w in b.WEATHER:
        p[w] = np.arange(n, dtype=float)
    return p


def test_lags_and_targets_and_no_leakage():
    aqi = [float(100 + i) for i in range(20)]
    f = b.add_features(_panel(aqi))
    t = 15
    row = f.iloc[t]
    for k in range(7):
        assert row[f"aqi_lag{k}"] == aqi[t - k]
    for h in (1, 2, 3):
        assert row[f"aqi_t+{h}"] == aqi[t + h]
    assert row["aqi_roll7"] == pytest.approx(np.mean(aqi[t - 6 : t + 1]))
    assert row["aqi_roll14"] == pytest.approx(np.mean(aqi[t - 13 : t + 1]))
    assert np.isnan(f.iloc[5]["aqi_roll7"])  # incomplete window is missing, not partial

    # Changing future days must not change any feature at t
    future = list(aqi)
    for i in range(t + 1, len(future)):
        future[i] = 999.0
    p2 = _panel(future)
    p2.loc[t + 1 :, [f"{x}_mean" for x in POLS] + b.WEATHER] = -5.0
    f2 = b.add_features(p2)
    cols = b.feature_columns()
    pd.testing.assert_series_equal(f.iloc[t][cols], f2.iloc[t][cols], check_names=False)


def test_missing_day_is_missing_lag_not_previous_row():
    aqi = [float(100 + i) for i in range(10)]
    aqi[4] = np.nan
    f = b.add_features(_panel(aqi))
    assert np.isnan(f.iloc[5]["aqi_lag1"])
    assert f.iloc[5]["aqi_lag2"] == aqi[3]


def test_regions_do_not_bleed_into_each_other():
    a = _panel([100.0] * 10)
    c = _panel([300.0] * 10)
    c["region_id"] = 2
    f = b.add_features(pd.concat([a, c], ignore_index=True))
    first_b = f[f["region_id"] == 2].iloc[0]
    assert np.isnan(first_b["aqi_lag1"])
    last_a = f[f["region_id"] == 1].iloc[-1]
    assert np.isnan(last_a["aqi_t+1"])


def test_split_boundaries():
    s = b.assign_split(
        pd.Series([date(2024, 10, 31), date(2024, 11, 1), date(2025, 11, 1), date(2026, 10, 29)])
    )
    assert list(s.iloc[:3]) == ["train", "val", "test"]
    assert pd.isna(s.iloc[3])
