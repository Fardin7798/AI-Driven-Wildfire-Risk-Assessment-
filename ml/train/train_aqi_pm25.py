"""Train the district x day PM2.5 sub-index forecaster (h = 1, 2, 3 days) and evaluate it once.

Reads aqi_dataset.parquet from ml/pipeline/build_aqi_dataset.py (target: CPCB PM2.5 sub-index of
the daily CAMS PM2.5 mean; features known at the end of day t). One XGBoost regressor per horizon.

Protocol (test is touched exactly once, after every choice is fixed):
  0. Purge: for horizon h, train/val rows whose target day t+h falls after their split's last
     day are not fitted on or scored for tuning (so no target day of a later split is used).
  1. Tuning: a fixed grid (objective x max_depth x min_child_weight) is fitted on `train` with
     early stopping on `val`; the config with the lowest val MAE is chosen per horizon.
  2. Refit: the chosen config is refitted on train + val with the early-stopped tree count.
  3. Test: the refitted model predicts `test` once. Predictions are clipped to the sub-index
     range [0, 500] (a rule fixed before training). Nothing is changed after this step.

Baselines on the same rows (never typed in): persistence (sub-index of day t) and seasonal-naive
(sub-index of day t+h-7). Reported per horizon (MAE, RMSE, MAE skill vs persistence with a 95%
day-block bootstrap interval), per season of the target day, and per district quartile of the
train-period mean sub-index (Q1 cleanest .. Q4 most polluted).

Writes to --out-dir:
  aqi_pm25_xgb_h{1,2,3}.json      XGBoost boosters (refitted on train + val)
  aqi_pm25_metadata.json          features, chosen configs, tree counts, sha256
  aqi_pm25_evaluation.json        tuning grid on val, model + baselines on test
  aqi_pm25_test_predictions.parquet  region_id, date, horizon, target, model, baselines
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import re
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb

VERSION = "aqi_pm25_xgb_v1"
HORIZONS = (1, 2, 3)
TARGETS = {h: f"pm25_si_t+{h}" for h in HORIZONS}
ID_COLS = ["region_id", "date", "split"]
# every feature must match one of these (past/same-day values, calendar, location)
FEATURE_PATTERNS = [
    r"pm25_si_lag[0-6]",
    r"pm25_si_roll(7|14)",
    r"(pm25|pm10|no2|so2|co|o3)_lag[0-2]",
    r"(temp_max|temp_mean|rh_mean|wind_max|precip_sum)(_lag1)?",
    r"doy_sin|doy_cos|month|weekday|lat|lon",
]
GRID = {
    "objective": ["reg:squarederror", "reg:absoluteerror"],
    "max_depth": [4, 6, 8],
    "min_child_weight": [1, 20],
}
FIXED = {
    "learning_rate": 0.05,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "tree_method": "hist",
    "n_estimators": 4000,
    "early_stopping_rounds": 100,
    "eval_metric": "mae",
    "random_state": 42,
    "n_jobs": -1,
}
SEASONS = {12: "winter", 1: "winter", 2: "winter", 3: "pre_monsoon", 4: "pre_monsoon"}
SEASONS |= {5: "pre_monsoon", 6: "monsoon", 7: "monsoon", 8: "monsoon", 9: "monsoon"}
SEASONS |= {10: "post_monsoon", 11: "post_monsoon"}
N_BOOT = 1000


def mae(e: np.ndarray) -> float:
    return round(float(np.mean(np.abs(e))), 3)


def rmse(e: np.ndarray) -> float:
    return round(float(np.sqrt(np.mean(e**2))), 3)


def feature_columns(df: pd.DataFrame) -> list[str]:
    cols = [c for c in df.columns if c not in ID_COLS and c not in TARGETS.values()]
    for c in cols:
        if not any(re.fullmatch(p, c) for p in FEATURE_PATTERNS):
            raise ValueError(f"unexpected column {c!r}: not a known past/same-day feature")
    return cols


def leakage_checks(df: pd.DataFrame) -> dict:
    """Data-level checks that features are day <= t and targets are day t+h."""
    d = df.sort_values(["region_id", "date"])
    nxt = d.groupby("region_id")["pm25_si_lag0"].shift(-1)
    nxt_date = d.groupby("region_id")["date"].shift(-1)
    consecutive = (pd.to_datetime(nxt_date) - pd.to_datetime(d["date"])).dt.days == 1
    lag1_next = d.groupby("region_id")["pm25_si_lag1"].shift(-1)
    out = {
        # t+1 target equals the next row's same-day sub-index wherever the next day exists
        "target_h1_equals_next_day_lag0": bool((d["pm25_si_t+1"] == nxt)[consecutive].all()),
        # lag1 of day t+1 equals lag0 of day t (time ordering of lags)
        "lag1_of_next_equals_lag0": bool((lag1_next == d["pm25_si_lag0"])[consecutive].all()),
        "max_train_date": str(df.loc[df["split"] == "train", "date"].max()),
        "min_val_date": str(df.loc[df["split"] == "val", "date"].min()),
        "max_val_date": str(df.loc[df["split"] == "val", "date"].max()),
        "min_test_date": str(df.loc[df["split"] == "test", "date"].min()),
    }
    if not (out["target_h1_equals_next_day_lag0"] and out["lag1_of_next_equals_lag0"]):
        raise ValueError(f"leakage/time-order check failed: {out}")
    if (
        not out["max_train_date"]
        < out["min_val_date"]
        <= out["max_val_date"]
        < out["min_test_date"]
    ):
        raise ValueError(f"splits overlap: {out}")
    return out


def skill_ci(err_model: np.ndarray, err_ref: np.ndarray, dates: np.ndarray) -> dict:
    """MAE skill (1 - MAE_model / MAE_ref) with a 95% bootstrap interval over days."""
    frame = pd.DataFrame({"d": dates, "m": np.abs(err_model), "r": np.abs(err_ref)})
    per_day = frame.groupby("d")[["m", "r"]].sum()
    ms, rs = per_day["m"].to_numpy(), per_day["r"].to_numpy()
    rng = np.random.default_rng(0)
    idx = rng.integers(0, len(ms), size=(N_BOOT, len(ms)))
    boot = 1 - ms[idx].sum(1) / rs[idx].sum(1)
    return {
        "skill": round(float(1 - ms.sum() / rs.sum()), 4),
        "ci95": [
            round(float(np.percentile(boot, 2.5)), 4),
            round(float(np.percentile(boot, 97.5)), 4),
        ],
    }


def purge(part: pd.DataFrame, h: int, end) -> pd.DataFrame:
    """Rows whose target day (t + h) lies inside the split, so no target crosses a boundary."""
    target_day = pd.to_datetime(part["date"]) + pd.Timedelta(days=h)
    return part[(target_day <= pd.Timestamp(end)).to_numpy()]


def tune(train: pd.DataFrame, val: pd.DataFrame, feats: list[str], h: int) -> tuple[dict, list]:
    y_tr, y_va = train[TARGETS[h]].to_numpy(float), val[TARGETS[h]].to_numpy(float)
    trials = []
    for values in itertools.product(*GRID.values()):
        cfg = dict(zip(GRID.keys(), values, strict=True))
        m = xgb.XGBRegressor(**cfg, **FIXED)
        m.fit(train[feats], y_tr, eval_set=[(val[feats], y_va)], verbose=False)
        p = np.clip(m.predict(val[feats]), 0, 500)
        trials.append(
            {
                **cfg,
                "best_iteration": int(m.best_iteration),
                "val_mae": mae(p - y_va),
                "val_rmse": rmse(p - y_va),
            }
        )
        print(f"h{h} {trials[-1]}", flush=True)
    best = min(trials, key=lambda t: t["val_mae"])
    return best, trials


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dataset", type=Path, required=True)
    ap.add_argument("--out-dir", type=Path, required=True)
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_parquet(args.dataset)
    df["date"] = pd.to_datetime(df["date"]).dt.date
    feats = feature_columns(df)
    checks = leakage_checks(df)
    train, val, test = (
        df[df["split"] == s].reset_index(drop=True) for s in ("train", "val", "test")
    )
    trainval = pd.concat([train, val], ignore_index=True)

    # district quartiles from the train period only
    dmean = train.groupby("region_id")[TARGETS[1]].mean()
    quart = pd.qcut(dmean, 4, labels=["Q1", "Q2", "Q3", "Q4"]).astype(str)

    evaluation: dict = {
        "version": VERSION,
        "rows": {"train": len(train), "val": len(val), "test": len(test)},
        "n_features": len(feats),
        "leakage_checks": checks,
        "district_quartile_bounds_train_mean_si": {
            q: [round(float(dmean[quart == q].min()), 2), round(float(dmean[quart == q].max()), 2)]
            for q in ["Q1", "Q2", "Q3", "Q4"]
        },
        "tuning": {},
        "val": {},
        "test": {},
    }
    meta: dict = {"version": VERSION, "features": feats, "horizons": {}}
    preds = []

    # ---- 1+2: tune on val, refit on train+val (test is not read here)
    models = {}
    train_end, val_end = train["date"].max(), val["date"].max()
    for h in HORIZONS:
        tr_h, va_h = purge(train, h, train_end), purge(val, h, val_end)
        tv_h = purge(trainval, h, val_end)
        best, trials = tune(tr_h, va_h, feats, h)
        evaluation["tuning"][f"h{h}"] = {
            "rows_fit": len(tr_h),
            "rows_val": len(va_h),
            "rows_refit": len(tv_h),
            "chosen": best,
            "grid": trials,
        }
        y_va = va_h[TARGETS[h]].to_numpy(float)
        evaluation["val"][f"h{h}"] = {
            "model_train_only": {"mae": best["val_mae"], "rmse": best["val_rmse"]},
            "persistence": {
                "mae": mae(va_h["pm25_si_lag0"].to_numpy(float) - y_va),
                "rmse": rmse(va_h["pm25_si_lag0"].to_numpy(float) - y_va),
            },
            "seasonal_naive": {
                "mae": mae(va_h[f"pm25_si_lag{7 - h}"].to_numpy(float) - y_va),
                "rmse": rmse(va_h[f"pm25_si_lag{7 - h}"].to_numpy(float) - y_va),
            },
        }
        cfg = {k: best[k] for k in GRID}
        fixed = {
            k: v for k, v in FIXED.items() if k not in ("n_estimators", "early_stopping_rounds")
        }
        m = xgb.XGBRegressor(**cfg, **fixed, n_estimators=best["best_iteration"] + 1)
        m.fit(tv_h[feats], tv_h[TARGETS[h]].to_numpy(float), verbose=False)
        models[h] = m
        path = args.out_dir / f"aqi_pm25_xgb_h{h}.json"
        m.save_model(path)
        meta["horizons"][f"h{h}"] = {
            "config": cfg,
            "n_trees": best["best_iteration"] + 1,
            "file": path.name,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }

    # ---- 3: test, once
    test_dates = pd.to_datetime(test["date"])
    for h in HORIZONS:
        y = test[TARGETS[h]].to_numpy(float)
        pred = np.clip(models[h].predict(test[feats]), 0, 500)
        cands = {
            "model": pred,
            "persistence": test["pm25_si_lag0"].to_numpy(float),
            "seasonal_naive": test[f"pm25_si_lag{7 - h}"].to_numpy(float),
        }
        errs = {k: v - y for k, v in cands.items()}
        season = (test_dates + pd.Timedelta(days=h)).dt.month.map(SEASONS).to_numpy()
        q = test["region_id"].map(quart).to_numpy()
        res: dict = {k: {"mae": mae(e), "rmse": rmse(e)} for k, e in errs.items()}
        res["skill_vs_persistence"] = skill_ci(
            errs["model"], errs["persistence"], test["date"].to_numpy()
        )
        res["skill_vs_seasonal_naive"] = skill_ci(
            errs["model"], errs["seasonal_naive"], test["date"].to_numpy()
        )
        res["by_season"] = {
            s: {"n": int((season == s).sum()), **{k: mae(e[season == s]) for k, e in errs.items()}}
            for s in sorted(set(season))
        }
        res["by_district_quartile"] = {
            g: {
                "n": int((q == g).sum()),
                "districts": int(test.loc[q == g, "region_id"].nunique()),
                **{k: mae(e[q == g]) for k, e in errs.items()},
            }
            for g in ["Q1", "Q2", "Q3", "Q4"]
        }
        evaluation["test"][f"h{h}"] = res
        preds.append(
            pd.DataFrame(
                {
                    "region_id": test["region_id"],
                    "date": test["date"],
                    "horizon": h,
                    "target_date": (test_dates + pd.Timedelta(days=h)).dt.date,
                    "target": y,
                    **cands,
                }
            )
        )

    meta["trained_at"] = datetime.now(UTC).isoformat()
    meta["xgboost"] = xgb.__version__
    (args.out_dir / "aqi_pm25_metadata.json").write_text(json.dumps(meta, indent=2))
    (args.out_dir / "aqi_pm25_evaluation.json").write_text(json.dumps(evaluation, indent=2))
    pd.concat(preds, ignore_index=True).to_parquet(
        args.out_dir / "aqi_pm25_test_predictions.parquet", index=False
    )
    print(json.dumps({k: evaluation[k] for k in ("rows", "leakage_checks", "test")}, indent=2))


if __name__ == "__main__":
    main()
