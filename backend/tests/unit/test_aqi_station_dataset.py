"""AQI station pipeline: CAMS daily rules and station QC (ml/pipeline/aqi_sources.py), station
merging, no-leakage features and alignment (build_aqi_station_dataset.py), and the trainer's
pure helpers (ml/train/train_aqi_station.py)."""

import sys
from datetime import date
from pathlib import Path

import numpy as np
import pytest

pd = pytest.importorskip("pandas")

ML = Path(__file__).resolve().parents[3] / "ml"
sys.path.insert(0, str(ML / "pipeline"))
sys.path.insert(0, str(ML / "train"))
import aqi_sources as b  # noqa: E402
import build_aqi_station_dataset as bs  # noqa: E402
import train_aqi_station as tr  # noqa: E402

from app.domain.aqi import calculate_sub_index, get_aqi_category  # noqa: E402

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


def test_station_exclusion_rules():
    d = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=10, freq="D").strftime("%Y-%m-%d"),
            "value": [10.0, 0.0, 985.0, 1200.0, 984.0, 7.0, 7.0, 7.0, 7.0, 7.0],
            "pct_complete": [80.0, 80.0, 80.0, 80.0, 74.0, 90.0, 90.0, 90.0, 90.0, 90.0],
        }
    )
    m = b.station_exclusions(d)
    drop = pd.concat(m, axis=1).any(axis=1)
    assert list(drop) == [False, True, True, True, True, True, True, True, True, True]
    assert m["stuck_run_ge_5"].sum() == 5
    assert b.STATION_CEILING == 985.0


def test_clean_station_days_counts_and_sorts():
    d = pd.DataFrame(
        {
            "date": ["2024-01-03", "2024-01-01", "2024-01-02"],
            "value": [20.0, 985.0, 30.0],
            "pct_complete": [90.0, 90.0, 50.0],
        }
    )
    kept, counts = b.clean_station_days(d)
    assert list(kept["date"]) == ["2024-01-03"]
    assert counts["value_eq_985"] == 1 and counts["pct_complete_lt_75"] == 1


# ---------------------------------------------------------------- stations
def test_cluster_locations_merges_copies_within_radius():
    locs = pd.DataFrame(
        {
            "location_id": [17, 7044, 236, 6358, 999],
            "lat": [28.5633, 28.5633, 28.6364, 28.6388, 19.0],  # 236/6358 ~ 270 m apart
            "lon": [77.1869, 77.1869, 77.2011, 77.2011, 72.8],
        }
    )
    m = bs.cluster_locations(locs)
    assert m[17] == m[7044] == 17
    assert m[236] == m[6358] == 236
    assert m[999] == 999
    assert bs.cluster_locations(locs, radius_m=100)[6358] == 6358


def test_station_daily_means_overlapping_sensors_and_counts_them():
    days = pd.DataFrame(
        {
            "station_id": [1, 1, 1, 1],
            "parameter": ["pm25"] * 4,
            "date": [date(2025, 1, 1), date(2025, 1, 1), date(2025, 1, 2), date(2025, 1, 2)],
            "value": [40.0, 60.0, 50.0, 50.0],
        }
    )
    out, stats = bs.station_daily(days)
    assert list(out["value"]) == [50.0, 50.0]
    assert stats["pm25"] == {
        "station_days": 2,
        "days_with_several_sensor_values": 2,
        "of_which_identical_values": 1,
    }


def _station_panel(si: list[float], station_id: int = 5) -> "pd.DataFrame":
    n = len(si)
    return pd.DataFrame(
        {
            "station_id": station_id,
            "date": pd.date_range("2025-03-01", periods=n, freq="D").date,
            "st_si": si,
            "st_pm10": [float(200 + i) for i in range(n)],
        }
    )


def _district_panel(n: int, region_id: int = 9, start: str = "2025-02-20") -> "pd.DataFrame":
    p = pd.DataFrame(
        {"region_id": region_id, "date": pd.date_range(start, periods=n, freq="D").date}
    )
    for pol in POLS:
        p[f"{pol}_mean"] = np.arange(n, dtype=float)
    p["pm25_si"] = np.arange(n, dtype=float) + 1000
    for w in b.WEATHER:
        p[w] = np.arange(n, dtype=float)
    return p


_META = pd.DataFrame({"station_id": [5], "region_id": [9], "lat": [21.0], "lon": [75.5]})


def _features(si: list[float], dist: "pd.DataFrame") -> "pd.DataFrame":
    return bs.combine(bs.station_features(_station_panel(si)), bs.district_features(dist), _META)


def test_station_features_targets_and_no_leakage():
    si = [float(100 + i) for i in range(40)]
    dist = _district_panel(60)
    f = _features(si, dist)
    t = 35
    row = f.iloc[t]
    for k in range(7):
        assert row[f"st_si_lag{k}"] == si[t - k]
    for h in (1, 2, 3):
        assert row[f"pm25_si_t+{h}"] == si[t + h]
    assert row["st_si_roll7"] == pytest.approx(np.mean(si[t - 6 : t + 1]))
    assert row["st_si_roll30"] == pytest.approx(np.mean(si[t - 29 : t + 1]))
    assert row["st_pm10_lag2"] == 200 + t - 2

    # perturb every station and district value after day t: features at t must not change
    future = list(si)
    for i in range(t + 1, len(future)):
        future[i] = 999.0
    d2 = dist.copy()
    later = pd.to_datetime(d2["date"]) > pd.Timestamp(row["date"])
    d2.loc[later, [*[f"{p}_mean" for p in POLS], "pm25_si", *b.WEATHER]] = -5.0
    p2 = _station_panel(future)
    p2.loc[t + 1 :, "st_pm10"] = -5.0
    f2 = bs.combine(bs.station_features(p2), bs.district_features(d2), _META)
    cols = bs.feature_columns(f)
    pd.testing.assert_series_equal(f.iloc[t][cols], f2.iloc[t][cols], check_names=False)
    assert not set(cols) & set(bs.TARGETS) and not set(cols) & set(bs.REFERENCE)


def test_alignment_station_to_its_district_and_day():
    si = [float(100 + i) for i in range(40)]
    dist = _district_panel(60)  # starts 9 days before the station series
    f = _features(si, dist)
    row = f.iloc[20]
    offset = (pd.Timestamp(row["date"]) - pd.Timestamp("2025-02-20")).days
    assert row["region_id"] == 9 and (row["lat"], row["lon"]) == (21.0, 75.5)
    assert row["cams_pm25_si_lag0"] == 1000 + offset
    assert row["cams_pm25_si_lag6"] == 1000 + offset - 6
    assert row["cams_no2_lag2"] == offset - 2 and row["temp_max_lag1"] == offset - 1
    assert row["ref_cams_si_t+2"] == 1000 + offset + 2
    assert row["bias_si_lag0"] == si[20] - (1000 + offset)
    # CAMS lags of the station's first day come from district days before the station started
    assert f.iloc[0]["cams_pm25_si_lag6"] == 1000 + 9 - 6
    # a station in a district without CAMS rows gets NaN, never another district's values
    g = bs.combine(
        bs.station_features(_station_panel(si)), bs.district_features(_district_panel(60, 8)), _META
    )
    assert g["cams_pm25_si_lag0"].isna().all()


def test_missing_station_day_is_missing_lag_not_previous_row():
    si = [float(100 + i) for i in range(30)]
    si[24] = np.nan
    f = _features(si, _district_panel(60))
    assert np.isnan(f.iloc[25]["st_si_lag1"]) and f.iloc[25]["st_si_lag2"] == si[23]
    assert f.iloc[25]["st_nvalid7"] == 6
    assert np.isnan(f.iloc[23]["pm25_si_t+1"])


def test_calendar_panel_fills_gaps_with_missing_rows():
    df = pd.DataFrame(
        {"station_id": [1, 1], "date": [date(2025, 1, 1), date(2025, 1, 4)], "v": [1.0, 4.0]}
    )
    p = bs.calendar_panel(df, "station_id")
    assert len(p) == 4 and p["v"].isna().sum() == 2


def test_no_station_features_exclude_every_station_input():
    f = _features([float(100 + i) for i in range(40)], _district_panel(60))
    cols = bs.feature_columns(f)
    no_station = [c for c in cols if not bs.station_feature(c)]
    assert not any(c.startswith(("st_", "bias_")) for c in no_station)
    assert {"cams_pm25_si_lag0", "temp_max", "lat", "doy_sin"} <= set(no_station)
    assert [tr.station_feature(c) for c in cols] == [bs.station_feature(c) for c in cols]
    f["split"] = "val"
    assert tr.feature_columns(f) == cols  # every builder feature is a known past feature


# ---------------------------------------------------------------- trainer helpers
def test_category_bins_match_cpcb_categories():
    names = ["Good", "Satisfactory", "Moderate", "Poor", "Very Poor", "Severe"]
    vals = np.array([0, 50, 50.4, 50.6, 100, 101, 200, 201, 300, 301, 400, 401, 500])
    got = tr.category(vals)
    want = [names.index(get_aqi_category(int(np.rint(v)))) for v in vals]
    assert list(got) == want


def test_fit_rows_purges_targets_on_or_after_cutoff():
    df = pd.DataFrame(
        {
            "date": [date(2025, 10, 29), date(2025, 10, 30), date(2025, 10, 31)],
            "pm25_si_t+1": [1.0, 2.0, np.nan],
            "pm25_si_t+2": [1.0, 2.0, 3.0],
        }
    )
    assert list(tr.fit_rows(df, 1, date(2025, 11, 1))["date"]) == df["date"][:2].tolist()
    assert list(tr.fit_rows(df, 2, date(2025, 11, 1))["date"]) == [date(2025, 10, 29)]


def test_test_months_and_seasons():
    months = tr.month_starts(*tr.TEST)
    assert months[0] == date(2025, 11, 1) and months[-1] == date(2026, 10, 1) and len(months) == 12
    assert tr.SEASONS == b.SEASONS
    assert tr.VAL[0] == b.SPLITS["val"][0] and tr.TEST == b.SPLITS["test"]
    assert tr.TRAIN_END == b.SPLITS["train"][1]


def test_metrics_r2_and_category_accuracy():
    y = np.array([40.0, 80.0, 150.0, 250.0])
    m = tr.metrics(y.copy(), y)
    assert m["mae"] == 0 and m["r2"] == 1 and m["category_accuracy"] == 1
    m2 = tr.metrics(np.array([60.0, 80.0, 150.0, 250.0]), y)
    assert m2["mae"] == 5 and m2["category_accuracy"] == 0.75


def test_pm25_sub_index_cpcb_breakpoints():
    # CPCB NAQI PM2.5 (24-h, µg/m³): 0-30 Good, 31-60, 61-90, 91-120, 121-250, >250 Severe
    known = {0: 0, 30: 50, 31: 51, 45: 75, 60: 100, 61: 101, 75: 149, 90: 200, 91: 201}
    known |= {120: 300, 121: 301, 250: 400, 251: 401, 300: 420, 500: 500, 750: 500}
    assert {c: calculate_sub_index("pm25", float(c)) for c in known} == known


def test_grid_selection_and_edges():
    assert len(tr.grid_configs(dry=False)) == 120 and len(tr.grid_configs(dry=True)) == 2
    trials = [{**c, "mae": 2.0} for c in tr.grid_configs(dry=False)]
    trials[7]["mae"] = trials[9]["mae"] = 1.0
    best, edge = tr.select(trials)
    assert best is trials[7]  # lowest val MAE, first in grid order on a tie
    assert set(edge) == {"max_depth", "min_child_weight"}


def _tiny_frame() -> "pd.DataFrame":
    rng = np.random.default_rng(0)
    days = pd.date_range("2025-05-01", "2025-11-30").date
    df = pd.DataFrame({"station_id": 1, "region_id": 1, "date": days, "split": "x"})
    df["st_si_lag0"] = rng.uniform(20, 200, len(df))
    df["cams_pm25_si_lag0"] = df["st_si_lag0"] + rng.normal(0, 10, len(df))
    for h in tr.HORIZONS:
        df[f"pm25_si_t+{h}"] = df["st_si_lag0"].shift(-h)
        df[f"ref_cams_si_t+{h}"] = df["cams_pm25_si_lag0"].shift(-h)
    return df


def test_worker_tasks_are_deterministic_on_cpu(tmp_path):
    pytest.importorskip("xgboost")
    df = _tiny_frame()
    tr._W.update(df=df, feats=tr.variant_features(df), device="cpu", dry=True)
    train, val = tr.tuning_rows(df, 1)
    assert tr.target_day(train, 1).max() <= pd.Timestamp(tr.TRAIN_END)
    assert val["date"].min() >= tr.VAL[0] and tr.target_day(val, 1).max() <= pd.Timestamp(tr.VAL[1])
    cfg = tr.grid_configs(dry=True)[0]
    t1, t2 = tr.tune_task("with_station", 1, cfg), tr.tune_task("with_station", 1, cfg)
    assert t1 == t2 and t1["n_trees"] <= tr.DRY_TREES
    rows = tr.fit_rows(df, 1, date(2025, 11, 1))
    idx = df.index[df["date"] >= date(2025, 11, 1)].to_numpy()
    best = {**cfg, "n_trees": 3}
    p1 = tr.fit_predict_task("no_station", 1, best, rows.index.to_numpy(), idx, "t")
    p2 = tr.fit_predict_task("no_station", 1, best, rows.index.to_numpy(), idx, "t")
    assert np.array_equal(p1, p2) and len(p1) == len(idx) and (p1 >= 0).all()
    info = tr.final_task("no_station", 1, best, rows.index.to_numpy(), tmp_path / "m.json")
    assert len(info["sha256"]) == 64 and (tmp_path / "m.json").exists()
    tr._W.clear()
