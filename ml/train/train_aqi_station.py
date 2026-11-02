"""Train and evaluate the station PM2.5 sub-index forecasters (h = 1, 2, 3 days).

Reads aqi_station_dataset.parquet from ml/pipeline/build_aqi_station_dataset.py. Target: CPCB
PM2.5 sub-index measured at a CPCB station on day t+h. Two XGBoost variants per horizon:
  A "with_station": every feature (station lags, CAMS, weather, calendar, location)
  B "no_station":   no station-derived feature (st_*, bias_*): CAMS + weather + calendar + location
Missing inputs stay NaN (XGBoost's native missing handling); nothing is imputed.

Protocol (fixed before any test row is read):
  0. Purge: a row (t, h) may be fitted on only if its target day t+h is before the cutoff.
  1. Tuning: grid fitted on train (t+h <= 2025-06-30) with early stopping on val
     (t in 2025-07-01..2025-10-31, t+h <= 2025-10-31); lowest val MAE wins, per variant and h.
  2. Test (2025-11-01..2026-10-28), scored once, by an expanding window: for each calendar month
     m of the test year the chosen config (tree count fixed at the early-stopped count) is
     refitted on every row with t+h < first day of m, then predicts the rows with t in m. No row
     after the cutoff is ever fitted on. Predictions are clipped to [0, 500].
  3. Spatial check of B: GroupKFold (5 folds, groups = district) over all rows with
     t+h <= 2025-10-31, chosen B config: each fold predicts districts it never saw.
  4. Final artifacts: chosen configs refitted on every labelled row (after scoring; these models
     have no score of their own beyond the rolling test above).

Baselines on the same rows (never typed in): station persistence (sub-index of day t),
station seasonal-naive (day t+h-7), raw CAMS district sub-index of day t (a real forecast),
raw CAMS sub-index on the target day (reference only: not known at forecast time), and the
CAMS-target model v1 test predictions (--v1-predictions, joined on district, day t and h).
Metrics: MAE, RMSE, R2, CPCB category accuracy (0-50, 51-100, 101-200, 201-300, 301-400, >400 on
the rounded value), per horizon, per season of the target day, per station pollution quartile
(mean target before the test year), and MAE skill with a 95% day-block bootstrap interval.

Hardware: every model fit (tuning grid, monthly refits, spatial folds, final refits) runs in one
worker process per --devices entry (default cuda:0 and cuda:1, Kaggle T4 x2); each worker verifies
its XGBoost booster really runs on its device before any fit. The main process only loads data,
computes baselines and metrics. Tasks are collected in a fixed order, so results do not depend on
which worker ran a task (both workers are the same GPU model with the same seed).

--dry-run checks the wiring: real XGBoost with DRY_TREES trees, the first DRY_CONFIGS grid configs,
on whatever device is given (e.g. --devices cpu,cpu locally). Its output is not a result.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import multiprocessing as mp
import os
import re
import subprocess
import time
from concurrent.futures import Future, ProcessPoolExecutor
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

VERSION = "aqi_station_xgb_v1"
HORIZONS = (1, 2, 3)
TARGETS = {h: f"pm25_si_t+{h}" for h in HORIZONS}
REFERENCE = {h: f"ref_cams_si_t+{h}" for h in HORIZONS}
ID_COLS = ["station_id", "region_id", "date", "split"]
FEATURE_PATTERNS = [
    r"st_si_lag[0-6]",
    r"st_si_roll(7|14|30)",
    r"st_nvalid7",
    r"st_pm10_lag[0-2]",
    r"bias_si_(lag0|roll7)",
    r"cams_pm25_si_lag[0-6]",
    r"cams_pm25_si_roll(7|14)",
    r"cams_(pm25|pm10|no2|so2|co|o3)_lag[0-2]",
    r"(temp_max|temp_mean|rh_mean|wind_max|precip_sum)(_lag1)?",
    r"doy_sin|doy_cos|month|weekday|lat|lon",
]
TRAIN_END = date(2025, 6, 30)
VAL = (date(2025, 7, 1), date(2025, 10, 31))
TEST = (date(2025, 11, 1), date(2026, 10, 28))
GRID = {
    "objective": ["reg:squarederror", "reg:absoluteerror"],
    "max_depth": [3, 4, 5, 6, 8, 10],
    "min_child_weight": [5, 20, 50, 100, 300],
    "colsample_bytree": [0.6, 0.9],
}
FIXED = {
    "learning_rate": 0.05,
    "subsample": 0.8,
    "tree_method": "hist",
    "eval_metric": "mae",
    "random_state": 42,
    "n_jobs": 2,  # host threads per worker (4 vCPUs, 2 workers)
}
MAX_TREES, EARLY_STOP = 4000, 150
DEVICES = ("cuda:0", "cuda:1")
DRY_TREES, DRY_CONFIGS = 3, 2
SEASONS = {12: "winter", 1: "winter", 2: "winter", 3: "pre_monsoon", 4: "pre_monsoon"}
SEASONS |= {5: "pre_monsoon", 6: "monsoon", 7: "monsoon", 8: "monsoon", 9: "monsoon"}
SEASONS |= {10: "post_monsoon", 11: "post_monsoon"}
CATEGORY_EDGES = [50, 100, 200, 300, 400]  # CPCB: Good .. Severe, upper bounds inclusive
N_BOOT = 1000
N_SPATIAL_FOLDS = 5


# ---------------------------------------------------------------- features / rows
def station_feature(col: str) -> bool:
    return col.startswith(("st_", "bias_"))


def feature_columns(df: pd.DataFrame) -> list[str]:
    skip = set(ID_COLS) | set(TARGETS.values()) | set(REFERENCE.values())
    cols = [c for c in df.columns if c not in skip]
    for c in cols:
        if not any(re.fullmatch(p, c) for p in FEATURE_PATTERNS):
            raise ValueError(f"unexpected column {c!r}: not a known past/same-day feature")
    return cols


def target_day(df: pd.DataFrame, h: int) -> pd.Series:
    return pd.to_datetime(df["date"]) + pd.Timedelta(days=h)


def fit_rows(df: pd.DataFrame, h: int, before: date) -> pd.DataFrame:
    """Rows with a target whose target day t+h is strictly before `before`."""
    ok = df[TARGETS[h]].notna() & (target_day(df, h) < pd.Timestamp(before))
    return df[ok.to_numpy()]


def month_starts(lo: date, hi: date) -> list[date]:
    return [d.date() for d in pd.date_range(lo, hi, freq="MS")]


def leakage_checks(df: pd.DataFrame) -> dict:
    """Data-level checks: target h1 of day t is the next day's lag0, lag1 of t+1 is lag0 of t."""
    d = df.sort_values(["station_id", "date"])
    g = d.groupby("station_id")
    consecutive = (pd.to_datetime(g["date"].shift(-1)) - pd.to_datetime(d["date"])).dt.days == 1
    nxt0, nxt1 = g["st_si_lag0"].shift(-1), g["st_si_lag1"].shift(-1)
    both = consecutive & d["pm25_si_t+1"].notna() & nxt0.notna()
    both1 = consecutive & nxt1.notna() & d["st_si_lag0"].notna()
    out = {
        "target_h1_equals_next_day_lag0": bool((d["pm25_si_t+1"] == nxt0)[both].all()),
        "pairs_checked_target": int(both.sum()),
        "lag1_of_next_equals_lag0": bool((nxt1 == d["st_si_lag0"])[both1].all()),
        "pairs_checked_lag": int(both1.sum()),
    }
    if not (out["target_h1_equals_next_day_lag0"] and out["lag1_of_next_equals_lag0"]):
        raise ValueError(f"leakage/time-order check failed: {out}")
    return out


# ---------------------------------------------------------------- metrics
def category(v: np.ndarray) -> np.ndarray:
    return np.searchsorted(CATEGORY_EDGES, np.rint(v), side="left")


def metrics(pred: np.ndarray, y: np.ndarray) -> dict:
    e = pred - y
    sst = float(np.sum((y - y.mean()) ** 2))
    return {
        "n": int(len(y)),
        "mae": round(float(np.mean(np.abs(e))), 3),
        "rmse": round(float(np.sqrt(np.mean(e**2))), 3),
        "r2": round(1 - float(np.sum(e**2)) / sst, 4) if sst > 0 else None,
        "bias": round(float(np.mean(e)), 3),
        "category_accuracy": round(float(np.mean(category(pred) == category(y))), 4),
    }


def metrics_present(p: pd.DataFrame, col: str) -> dict:
    """Metrics of one candidate on every row where it and the target are present."""
    r = p.dropna(subset=["target", col])
    return metrics(r[col].to_numpy(float), r["target"].to_numpy(float))


def skill_ci(err_model: np.ndarray, err_ref: np.ndarray, days: np.ndarray) -> dict:
    """MAE skill (1 - MAE_model / MAE_ref) with a 95% bootstrap interval over days."""
    frame = pd.DataFrame({"d": days, "m": np.abs(err_model), "r": np.abs(err_ref)})
    per_day = frame.groupby("d")[["m", "r"]].sum()
    ms, rs = per_day["m"].to_numpy(), per_day["r"].to_numpy()
    rng = np.random.default_rng(0)
    idx = rng.integers(0, len(ms), size=(N_BOOT, len(ms)))
    boot = 1 - ms[idx].sum(1) / rs[idx].sum(1)
    return {
        "skill": round(float(1 - ms.sum() / rs.sum()), 4),
        "ci95": [round(float(np.percentile(boot, q)), 4) for q in (2.5, 97.5)],
    }


def score_table(p: pd.DataFrame, cands: list[str], skill_refs: list[tuple[str, str]]) -> dict:
    """Metrics for `cands` on the rows where all of them (and the target) are present."""
    rows = p.dropna(subset=["target", *cands])
    if rows.empty:
        return {"n": 0}
    y = rows["target"].to_numpy(float)
    out: dict = {
        "n": int(len(rows)),
        "stations": int(rows["station_id"].nunique()),
        "districts": int(rows["region_id"].nunique()),
        "overall": {c: metrics(rows[c].to_numpy(float), y) for c in cands},
        "skill": {
            f"{m}_vs_{r}": skill_ci(
                rows[m].to_numpy(float) - y, rows[r].to_numpy(float) - y, rows["date"].to_numpy()
            )
            for m, r in skill_refs
        },
    }
    for key in ("season", "quartile"):
        out[f"by_{key}"] = {
            g: {c: metrics(part[c].to_numpy(float), part["target"].to_numpy(float)) for c in cands}
            for g, part in rows.groupby(key)
        }
    return out


# ---------------------------------------------------------------- data / rows
def load_dataset(path: Path) -> pd.DataFrame:
    df = pd.read_parquet(path).reset_index(drop=True)
    df["date"] = pd.to_datetime(df["date"]).dt.date
    return df


def variant_features(df: pd.DataFrame) -> dict[str, list[str]]:
    feats_a = feature_columns(df)
    return {"with_station": feats_a, "no_station": [c for c in feats_a if not station_feature(c)]}


def tuning_rows(df: pd.DataFrame, h: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Train: t+h <= TRAIN_END. Val: t in VAL with t+h <= VAL end. Never a test row."""
    tr = fit_rows(df, h, TRAIN_END + timedelta(days=1))
    va = df[(df["date"] >= VAL[0]) & (df["date"] <= VAL[1])]
    return tr, fit_rows(va, h, VAL[1] + timedelta(days=1))


def grid_configs(dry: bool) -> list[dict]:
    combos = [dict(zip(GRID.keys(), v, strict=True)) for v in itertools.product(*GRID.values())]
    return combos[:DRY_CONFIGS] if dry else combos


# ---------------------------------------------------------------- GPU workers
_W: dict = {}  # per worker process: df, feats, device, dry


def _init_worker(dataset: Path, devices: mp.Queue, dry: bool) -> None:
    import xgboost as xgb

    device = devices.get()
    df = load_dataset(dataset)
    _W.update(df=df, feats=variant_features(df), device=device, dry=dry)
    probe = xgb.XGBRegressor(n_estimators=1, tree_method="hist", device=device)
    probe.fit(np.arange(16.0).reshape(-1, 1), np.arange(16.0))
    used = json.loads(probe.get_booster().save_config())["learner"]["generic_param"]["device"]
    if used != device:
        raise RuntimeError(f"worker asked for {device} but XGBoost runs on {used}")
    gpu = ""
    if device.startswith("cuda"):
        q = [
            "nvidia-smi",
            f"--id={device.split(':')[1]}",
            "--query-gpu=name,uuid",
            "--format=csv,noheader",
        ]
        gpu = subprocess.run(q, capture_output=True, text=True, check=True).stdout.strip()
    print(
        f"[worker pid={os.getpid()} device={device}] ready: booster device={used} {gpu} "
        f"xgboost={xgb.__version__} cuda_build={xgb.build_info().get('USE_CUDA')}",
        flush=True,
    )


def _model(cfg: dict, n_trees: int, early_stop: bool):
    import xgboost as xgb

    kw = {**cfg, **FIXED, "device": _W["device"]}
    kw["n_estimators"] = min(n_trees, DRY_TREES) if _W["dry"] else n_trees
    if early_stop:
        kw["early_stopping_rounds"] = EARLY_STOP
    return xgb.XGBRegressor(**kw)


def tune_task(name: str, h: int, cfg: dict) -> dict:
    """One grid config: fit on train with early stopping on val; val metrics."""
    tr, va = tuning_rows(_W["df"], h)
    feats = _W["feats"][name]
    y_tr, y_va = tr[TARGETS[h]].to_numpy(float), va[TARGETS[h]].to_numpy(float)
    m = _model(cfg, MAX_TREES, early_stop=True)
    m.fit(tr[feats], y_tr, eval_set=[(va[feats], y_va)], verbose=False)
    p = np.clip(m.predict(va[feats]), 0, 500)
    trial = {**cfg, "n_trees": int(m.best_iteration) + 1, **metrics(p, y_va)}
    print(f"[{_W['device']}] tune {name} h{h} {trial}", flush=True)
    return trial


def fit_predict_task(
    name: str, h: int, best: dict, fit_idx: np.ndarray, pred_idx: np.ndarray, tag: str
) -> np.ndarray:
    """Refit the chosen config (fixed tree count) on rows fit_idx; predict rows pred_idx."""
    df, feats = _W["df"], _W["feats"][name]
    rows, pred = df.iloc[fit_idx], df.iloc[pred_idx]
    m = _model({k: best[k] for k in GRID}, best["n_trees"], early_stop=False)
    m.fit(rows[feats], rows[TARGETS[h]].to_numpy(float), verbose=False)
    out = np.clip(m.predict(pred[feats]), 0, 500)
    print(f"[{_W['device']}] {tag} {name} h{h} fit={len(rows)} predict={len(pred)}", flush=True)
    return out


def final_task(name: str, h: int, best: dict, fit_idx: np.ndarray, path: Path) -> dict:
    """Refit the chosen config on every labelled row and save it."""
    df, feats = _W["df"], _W["feats"][name]
    rows = df.iloc[fit_idx]
    m = _model({k: best[k] for k in GRID}, best["n_trees"], early_stop=False)
    m.fit(rows[feats], rows[TARGETS[h]].to_numpy(float), verbose=False)
    m.save_model(path)
    gain = m.get_booster().get_score(importance_type="gain")
    print(f"[{_W['device']}] final {name} h{h} fit={len(rows)} -> {path.name}", flush=True)
    return {
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "top_gain_features": {
            k: round(float(v), 2) for k, v in sorted(gain.items(), key=lambda kv: -kv[1])[:15]
        },
    }


def select(trials: list[dict]) -> tuple[dict, dict]:
    """Lowest val MAE (first in grid order on a tie) and whether it sits on a grid edge."""
    best = min(trials, key=lambda t: t["mae"])
    edge = {k: best[k] in (v[0], v[-1]) for k, v in GRID.items() if len(v) > 2}
    return best, edge


# ---------------------------------------------------------------- main
def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dataset", type=Path, required=True)
    ap.add_argument("--v1-predictions", type=Path, default=None)
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--devices", default=",".join(DEVICES), help="one worker per device")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    dry, devices = args.dry_run, args.devices.split(",")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    timing: dict[str, float] = {}

    df = load_dataset(args.dataset)
    variants = variant_features(df)
    checks = leakage_checks(df)

    pre_test = df[df["date"] < TEST[0]]
    smean = pre_test.groupby("station_id")[TARGETS[1]].mean().dropna()
    quart = pd.qcut(smean, 4, labels=["Q1", "Q2", "Q3", "Q4"]).astype(str)

    evaluation: dict = {
        "version": VERSION,
        "dry_run": dry,
        "protocol": {
            "train_target_day_lte": str(TRAIN_END),
            "val_days": [str(VAL[0]), str(VAL[1])],
            "test_days": [str(TEST[0]), str(TEST[1])],
            "test_scoring": "expanding window, monthly refit on rows with t+h < month start",
            "grid": GRID,
            "fixed": {**FIXED, "max_trees": MAX_TREES, "early_stopping_rounds": EARLY_STOP},
            "devices": devices,
        },
        "features": {k: len(v) for k, v in variants.items()},
        "leakage_checks": checks,
        "station_quartile_bounds_pre_test_mean_si": {
            q: [round(float(smean[quart == q].min()), 2), round(float(smean[quart == q].max()), 2)]
            for q in ["Q1", "Q2", "Q3", "Q4"]
        },
        "tuning": {},
        "rolling_test_fits": {},
        "spatial_cv_no_station": {},
        "test": {},
    }
    meta: dict = {"version": VERSION, "features": variants, "models": {}}
    test = df[(df["date"] >= TEST[0]) & (df["date"] <= TEST[1])]
    tmonth = pd.to_datetime(test["date"]).dt.to_period("M")
    months = month_starts(TEST[0], TEST[1])

    ctx = mp.get_context("spawn")
    queue = ctx.Queue()
    for d in devices:
        queue.put(d)
    with ProcessPoolExecutor(
        len(devices), mp_context=ctx, initializer=_init_worker, initargs=(args.dataset, queue, dry)
    ) as pool:
        # ---- 1: tuning (test rows are not touched); results kept in grid order
        configs = grid_configs(dry)
        tune_f = {
            (name, h): [pool.submit(tune_task, name, h, cfg) for cfg in configs]
            for name in variants
            for h in HORIZONS
        }
        chosen: dict[tuple[str, int], dict] = {}
        for (name, h), futs in tune_f.items():
            trials = [f.result() for f in futs]
            best, edge = select(trials)
            chosen[(name, h)] = best
            tr, va = tuning_rows(df, h)
            evaluation["tuning"][f"{name}_h{h}"] = {
                "rows_fit": len(tr),
                "rows_val": len(va),
                "chosen": best,
                "chosen_at_grid_edge": edge,
                "grid": trials,
            }
            print(f"chosen {name} h{h}: {best} edge={edge}", flush=True)
        timing["tuning"] = round(time.time() - t0, 1)

        # ---- 2-4: every refit after selection (test, spatial CV, final)
        test_f: dict[tuple[date, str, int], tuple[np.ndarray, Future]] = {}
        for start in months:
            pred_idx = test.index[(tmonth == pd.Period(start, "M")).to_numpy()].to_numpy()
            for name in variants:
                for h in HORIZONS:
                    rows = fit_rows(df, h, start)
                    assert target_day(rows, h).max() < pd.Timestamp(start)
                    evaluation["rolling_test_fits"][f"{start}_{name}_h{h}"] = {
                        "rows_fit": len(rows),
                        "last_target_day": str(target_day(rows, h).max().date()),
                        "rows_predicted": len(pred_idx),
                    }
                    fut = pool.submit(
                        fit_predict_task,
                        name,
                        h,
                        chosen[(name, h)],
                        rows.index.to_numpy(),
                        pred_idx,
                        f"test {start}",
                    )
                    test_f[(start, name, h)] = (pred_idx, fut)
        from sklearn.model_selection import GroupKFold

        cv_f: dict[int, list] = {}
        for h in HORIZONS:
            rows = fit_rows(df, h, TEST[0])
            cv_f[h] = []
            folds = GroupKFold(n_splits=N_SPATIAL_FOLDS).split(rows, groups=rows["region_id"])
            for k, (tr_i, te_i) in enumerate(folds):
                fit_idx, pred_idx = rows.index[tr_i].to_numpy(), rows.index[te_i].to_numpy()
                fut = pool.submit(
                    fit_predict_task,
                    "no_station",
                    h,
                    chosen[("no_station", h)],
                    fit_idx,
                    pred_idx,
                    f"spatial fold {k}",
                )
                cv_f[h].append((k, pred_idx, fut))
        final_f = {}
        for name in variants:
            for h in HORIZONS:
                rows = df[df[TARGETS[h]].notna()]
                path = args.out_dir / f"aqi_station_{name}_h{h}.json"
                fut = pool.submit(
                    final_task, name, h, chosen[(name, h)], rows.index.to_numpy(), path
                )
                final_f[(name, h)] = (rows, path, fut)

        preds = {
            (name, h): pd.Series(np.nan, index=test.index) for name in variants for h in HORIZONS
        }
        for (_, name, h), (pred_idx, fut) in test_f.items():
            preds[(name, h)].loc[pred_idx] = fut.result()
        timing["test_refits_done"] = round(time.time() - t0, 1)
        cv_pred: dict[int, pd.Series] = {}
        cv_folds: dict[int, list] = {}
        for h in HORIZONS:
            rows = fit_rows(df, h, TEST[0])
            cv_pred[h] = pd.Series(np.nan, index=rows.index)
            cv_folds[h] = []
            for k, pred_idx, fut in cv_f[h]:
                cv_pred[h].loc[pred_idx] = fut.result()
                part = df.loc[pred_idx]
                cv_folds[h].append(
                    {
                        "fold": k,
                        "districts": int(part["region_id"].nunique()),
                        "stations": int(part["station_id"].nunique()),
                        **metrics(
                            cv_pred[h].loc[pred_idx].to_numpy(), part[TARGETS[h]].to_numpy(float)
                        ),
                    }
                )
        for (name, h), (rows, path, fut) in final_f.items():
            info = fut.result()
            meta["models"][f"{name}_h{h}"] = {
                "config": {k: chosen[(name, h)][k] for k in GRID},
                "n_trees": chosen[(name, h)]["n_trees"],
                "rows_fit": len(rows),
                "last_target_day": str(target_day(rows, h).max().date()),
                "file": path.name,
                **info,
            }
    timing["all_fits_done"] = round(time.time() - t0, 1)

    # ---- test scoring (main process, CPU): models vs baselines, scored once
    v1 = None
    if args.v1_predictions is not None:
        v1 = pd.read_parquet(args.v1_predictions)[["region_id", "date", "horizon", "model"]]
        v1["date"] = pd.to_datetime(v1["date"]).dt.date
        v1 = v1.rename(columns={"model": "cams_model_v1"})
    frames = []
    for h in HORIZONS:
        p = pd.DataFrame(
            {
                "station_id": test["station_id"],
                "region_id": test["region_id"],
                "date": test["date"],
                "horizon": h,
                "target": test[TARGETS[h]],
                "with_station": preds[("with_station", h)],
                "no_station": preds[("no_station", h)],
                "persistence": test["st_si_lag0"],
                "seasonal_naive": test[f"st_si_lag{7 - h}"],
                "cams_t": test["cams_pm25_si_lag0"],
                "cams_target_day_ref": test[REFERENCE[h]],
            }
        ).reset_index(drop=True)
        if v1 is not None:
            p = p.merge(
                v1[v1["horizon"] == h].drop(columns="horizon"), on=["region_id", "date"], how="left"
            )
        p["season"] = target_day(p, h).dt.month.map(SEASONS)
        p["quartile"] = p["station_id"].map(quart).fillna("no_pre_test_history")
        frames.append(p)
        a_cands = ["with_station", "no_station", "persistence", "seasonal_naive", "cams_t"]
        b_cands = ["no_station", "cams_t", "cams_target_day_ref"]
        if v1 is not None:
            b_cands.append("cams_model_v1")
        evaluation["test"][f"h{h}"] = {
            "all_rows_with_target": {c: metrics_present(p, c) for c in a_cands + b_cands[2:]},
            "table_with_station": score_table(
                p,
                a_cands,
                [
                    ("with_station", "persistence"),
                    ("with_station", "seasonal_naive"),
                    ("with_station", "no_station"),
                ],
            ),
            "table_no_station": score_table(
                p,
                b_cands,
                [("no_station", "cams_t")]
                + ([("no_station", "cams_model_v1")] if v1 is not None else []),
            ),
        }
    pd.concat(frames, ignore_index=True).to_parquet(
        args.out_dir / "aqi_station_test_predictions.parquet", index=False
    )

    # ---- spatial CV of the no-station model (pre-test rows only)
    for h in HORIZONS:
        rows = fit_rows(df, h, TEST[0])
        p = pd.DataFrame(
            {
                "station_id": rows["station_id"],
                "region_id": rows["region_id"],
                "date": rows["date"],
                "target": rows[TARGETS[h]],
                "no_station_unseen_district": cv_pred[h],
                "cams_t": rows["cams_pm25_si_lag0"],
                "cams_target_day_ref": rows[REFERENCE[h]],
                "season": target_day(rows, h).dt.month.map(SEASONS),
                "quartile": rows["station_id"].map(quart).fillna("no_pre_test_history"),
            }
        )
        evaluation["spatial_cv_no_station"][f"h{h}"] = {
            "rows": len(rows),
            "folds": cv_folds[h],
            "table": score_table(
                p,
                ["no_station_unseen_district", "cams_t", "cams_target_day_ref"],
                [("no_station_unseen_district", "cams_t")],
            ),
        }

    timing["total"] = round(time.time() - t0, 1)
    evaluation["wall_clock_seconds"] = timing
    import xgboost as xgb

    meta["trained_at"] = datetime.now(UTC).isoformat()
    meta["xgboost"] = xgb.__version__
    meta["devices"] = devices
    (args.out_dir / "aqi_station_metadata.json").write_text(json.dumps(meta, indent=2))
    (args.out_dir / "aqi_station_evaluation.json").write_text(json.dumps(evaluation, indent=2))
    summary = {
        h: {
            t: evaluation["test"][h][t].get("overall", {})
            for t in ("table_with_station", "table_no_station")
        }
        for h in evaluation["test"]
    }
    print(json.dumps(summary, indent=2))
    print(f"wall clock seconds: {timing}", flush=True)


if __name__ == "__main__":
    main()
