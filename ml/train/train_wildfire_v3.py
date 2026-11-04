"""Train wildfire_xgb_v3 (district x day fire-occurrence model) and evaluate it honestly.

Copy of the retired train_wildfire_v2.py (git history up to 431faf2); same features, params, seed and baselines. What changed:
  * weather input is ECMWF IFS HRES 9 km (the model live serving gets via Open-Meteo),
    built by ml/pipeline/prepare_ifs_weather.py + build_wildfire_dataset.py
  * split: train 2019-2023, validation 2024 (early stopping + thresholds),
    test 2025-01-01..2025-12-31 (never seen by any earlier model; reported once)
  * XGBoost device is a flag (cuda on Kaggle)
  * optional: the deployed wildfire_xgb_v2 is scored on the same 2025 test rows
    (IFS-weather rows = what live v2 actually receives; NASA POWER rows = v2's training
    weather), using v2's own thresholds and its served climatology (train 2019-2022).

Reads the table from ml/pipeline/build_wildfire_dataset.py.

Baselines are computed here, on the same test rows, never typed in:
  * fwi_only       - probability = FWI value (ranking only)
  * climatology    - district-month historical fire-day rate (train years)
  * persistence    - fires_prev_7d (any detection in the previous 7 days)

Writes to --out-dir:
  wildfire_xgb_v3.json              XGBoost booster
  wildfire_xgb_v3_metadata.json     features, thresholds, metrics, sha256, climatology
  wildfire_v3_evaluation.json       full metrics for model + baselines (val and test),
                                    plus v2-vs-v3 on the same 2025 rows when --v2-model is given
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
)

BACKEND = Path(__file__).resolve().parents[2] / "backend"
sys.path.insert(0, str(BACKEND))
from app.domain.features import WILDFIRE_V2_FEATURES  # noqa: E402

VERSION = "wildfire_xgb_v3"
TRAIN_YEARS = (2019, 2023)
VAL_YEAR = 2024
TEST_YEAR = 2025


def scores(y: np.ndarray, p: np.ndarray, threshold: float | None = None) -> dict:
    out = {
        "roc_auc": round(float(roc_auc_score(y, p)), 4),
        "pr_auc": round(float(average_precision_score(y, p)), 4),
        "positive_rate": round(float(y.mean()), 4),
        "n": int(len(y)),
    }
    if threshold is not None:
        yhat = (p >= threshold).astype(int)
        out.update(
            threshold=round(float(threshold), 4),
            precision=round(float(precision_score(y, yhat, zero_division=0)), 4),
            recall=round(float(recall_score(y, yhat, zero_division=0)), 4),
            f1=round(float(f1_score(y, yhat, zero_division=0)), 4),
        )
    if 0.0 <= p.min() and p.max() <= 1.0:
        out["brier"] = round(float(brier_score_loss(y, p)), 4)
    return out


def pick_thresholds(y: np.ndarray, p: np.ndarray) -> dict[str, float]:
    """Risk-class cut points chosen on the VALIDATION year only.

    high     = threshold that maximises F1
    moderate = highest threshold that still keeps recall >= 0.90
    extreme  = lowest threshold reaching precision >= 0.80 (else the 97.5th percentile)
    """
    prec, rec, thr = precision_recall_curve(y, p)
    prec, rec = prec[:-1], rec[:-1]
    f1 = 2 * prec * rec / np.clip(prec + rec, 1e-9, None)
    high = float(thr[int(np.argmax(f1))])
    ok_rec = thr[rec >= 0.90]
    moderate = float(ok_rec.max()) if len(ok_rec) else float(np.quantile(p, 0.5))
    ok_prec = thr[prec >= 0.80]
    extreme = float(ok_prec.min()) if len(ok_prec) else float(np.quantile(p, 0.975))
    moderate = min(moderate, high)
    extreme = max(extreme, high)
    return {"moderate": round(moderate, 4), "high": round(high, 4), "extreme": round(extreme, 4)}


def check_split_years(df: pd.DataFrame) -> None:
    """Refuse to train if the table's splits are not exactly the v3 protocol."""
    years = pd.to_datetime(df["date"]).dt.year
    want = {
        "train": set(range(TRAIN_YEARS[0], TRAIN_YEARS[1] + 1)),
        "val": {VAL_YEAR},
        "test": {TEST_YEAR},
    }
    for split, ys in want.items():
        got = set(years[df["split"] == split].unique().tolist())
        if got != ys:
            raise SystemExit(f"split {split}: years {sorted(got)} != protocol {sorted(ys)}")
    if set(df["split"].unique()) != set(want):
        raise SystemExit(f"unexpected splits {sorted(df['split'].unique())}")


def served_v2_climatology(rows: pd.DataFrame, v2_meta: dict) -> np.ndarray:
    """climatological_fire_freq as the live job computes it for v2 (v2 metadata climatology)."""
    rate = v2_meta["climatology"]["monthly_rate"]
    months = pd.to_datetime(rows["date"]).dt.month.values
    return np.array(
        [rate[g][m - 1] for g, m in zip(rows["gadm_id"].values, months, strict=True)],
        dtype=np.float32,
    )


def score_v2(
    v2: xgb.Booster, v2_meta: dict, rows: pd.DataFrame, feats: list[str], clim: str
) -> np.ndarray:
    x = rows[feats].copy()
    if clim == "served_v2":
        x["climatological_fire_freq"] = served_v2_climatology(rows, v2_meta)
    return v2.predict(xgb.DMatrix(x.values, feature_names=feats))


def compare_with_v2(args, te: pd.DataFrame, p_te: np.ndarray, feats: list[str]) -> dict:
    v2 = xgb.Booster()
    v2.load_model(args.v2_model)
    v2_meta = json.loads(args.v2_metadata.read_text())
    if v2_meta["feature_list"] != feats:
        raise SystemExit("v2 feature list differs from v3; cannot score v2 on these rows")
    v2_thr = v2_meta["thresholds"]["high"]
    te = te.assign(p_v3=p_te)
    out: dict = {
        "v2_sha256": hashlib.sha256(args.v2_model.read_bytes()).hexdigest(),
        "v2_threshold_high": v2_thr,
        "note": "v2 thresholds/climatology are v2's own (served); v3 uses its validation-year thresholds",
    }
    # (a) IFS-weather 2025 rows: identical rows for both models
    y = te.label.values
    out["ifs_weather_test_rows"] = {
        "n": int(len(te)),
        "v3": scores(y, te.p_v3.values, args._v3_thr),
        "v2_served_climatology": scores(y, score_v2(v2, v2_meta, te, feats, "served_v2"), v2_thr),
        "v2_v3_climatology": scores(y, score_v2(v2, v2_meta, te, feats, "dataset"), v2_thr),
    }
    # (b) NASA POWER-weather 2025 rows (v2's training weather), on the common (gadm_id, date) rows
    if args.power_dataset is not None:
        pw = pd.read_parquet(args.power_dataset)
        pw = pw[(pw.split == "test") & (pd.to_datetime(pw.date).dt.year == TEST_YEAR)]
        if pw[feats].isna().any().any():
            raise SystemExit("NaN features in POWER test rows")
        m = pw.merge(
            te[["gadm_id", "date", "label", "p_v3"]], on=["gadm_id", "date"], suffixes=("", "_ifs")
        )
        if not (m.label.values == m.label_ifs.values).all():
            raise SystemExit("labels differ between POWER and IFS tables on common rows")
        y = m.label.values
        out["power_weather_test_rows"] = {
            "n_power_rows": int(len(pw)),
            "n_common_with_ifs": int(len(m)),
            "v3_on_ifs_weather": scores(y, m.p_v3.values, args._v3_thr),
            "v2_on_power_served_climatology": scores(
                y, score_v2(v2, v2_meta, m, feats, "served_v2"), v2_thr
            ),
            "v2_on_power_v3_climatology": scores(
                y, score_v2(v2, v2_meta, m, feats, "dataset"), v2_thr
            ),
        }
    return out


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--dataset", type=Path, required=True)
    ap.add_argument("--climatology", type=Path, required=True)
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--fire-feature-source", default="VIIRS_NOAA20_NRT")
    ap.add_argument("--device", default="cuda", help="XGBoost device: cuda (Kaggle GPU) or cpu")
    ap.add_argument("--v2-model", type=Path, default=None, help="deployed wildfire_xgb_v2.json")
    ap.add_argument("--v2-metadata", type=Path, default=None)
    ap.add_argument(
        "--power-dataset",
        type=Path,
        default=None,
        help="same-protocol table built with NASA POWER weather (only its 2025 test rows are used)",
    )
    args = ap.parse_args()

    df = pd.read_parquet(args.dataset)
    feats = WILDFIRE_V2_FEATURES
    missing = [c for c in feats + ["label", "split"] if c not in df.columns]
    if missing:
        raise SystemExit(f"dataset missing columns: {missing}")
    if df[feats].isna().any().any():
        bad = df[feats].isna().sum()
        raise SystemExit(f"NaN features in dataset:\n{bad[bad > 0]}")
    check_split_years(df)

    tr, va, te = (df[df.split == s] for s in ("train", "val", "test"))
    dtr = xgb.DMatrix(tr[feats].values, label=tr.label.values, feature_names=feats)
    dva = xgb.DMatrix(va[feats].values, label=va.label.values, feature_names=feats)
    dte = xgb.DMatrix(te[feats].values, label=te.label.values, feature_names=feats)

    params = {
        "objective": "binary:logistic",
        "eval_metric": ["aucpr", "logloss"],
        "tree_method": "hist",
        "max_depth": 7,
        "eta": 0.05,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "min_child_weight": 20,
        "lambda": 1.0,
        "seed": 42,
        "nthread": 2,
        "device": args.device,
    }
    print(
        f"train={len(tr):,} val={len(va):,} test={len(te):,} pos_rate_train={tr.label.mean():.4f}"
    )
    booster = xgb.train(
        params,
        dtr,
        num_boost_round=2000,
        evals=[(dtr, "train"), (dva, "val")],
        early_stopping_rounds=50,
        verbose_eval=100,
    )
    best_it = booster.best_iteration
    p_va = booster.predict(dva, iteration_range=(0, best_it + 1))
    p_te = booster.predict(dte, iteration_range=(0, best_it + 1))
    thresholds = pick_thresholds(va.label.values, p_va)
    args._v3_thr = thresholds["high"]

    y_va, y_te = va.label.values, te.label.values
    evaluation = {
        "model": VERSION,
        "split": {
            "train": f"{TRAIN_YEARS[0]}-{TRAIN_YEARS[1]}",
            "validation": str(VAL_YEAR),
            "test": f"{TEST_YEAR}-01-01..{TEST_YEAR}-12-31",
        },
        "weather": "ECMWF IFS HRES 9 km daily (Open-Meteo archive, model ecmwf_ifs)",
        "xgboost_device": args.device,
        "label": "district-day has >=1 VIIRS NOAA-20 SP detection, confidence nominal/high, type 0",
        "best_iteration": int(best_it),
        "thresholds_from_validation": thresholds,
        "validation": {"xgboost": scores(y_va, p_va, thresholds["high"])},
        "test": {
            "xgboost": scores(y_te, p_te, thresholds["high"]),
            "fwi_only": scores(y_te, te.fwi.values),
            "climatology": scores(y_te, te.climatological_fire_freq.values),
            "persistence_fires_prev_7d": scores(y_te, te.fires_prev_7d.values),
        },
    }
    if args.v2_model is not None:
        evaluation["v2_vs_v3_same_2025_rows"] = compare_with_v2(args, te, p_te, feats)
    # Feature importance (gain) for the model card
    gain = booster.get_score(importance_type="gain")
    evaluation["feature_importance_gain"] = dict(
        sorted(((k, round(v, 2)) for k, v in gain.items()), key=lambda x: -x[1])
    )

    args.out_dir.mkdir(parents=True, exist_ok=True)
    # Save only the trees up to the early-stopping point
    final = booster[: best_it + 1]
    model_path = args.out_dir / f"{VERSION}.json"
    final.save_model(model_path)
    sha = hashlib.sha256(model_path.read_bytes()).hexdigest()

    clim = json.loads(args.climatology.read_text())
    test_m = evaluation["test"]["xgboost"]
    metadata = {
        "model_type": "wildfire",
        "version": VERSION,
        "model_name": VERSION,
        "algorithm": "XGBoost gradient boosted trees (binary:logistic)",
        "trained_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "sha256": sha,
        "feature_list": feats,
        "thresholds": thresholds,
        "metrics": {
            "test_year": TEST_YEAR,
            "roc_auc": test_m["roc_auc"],
            "pr_auc": test_m["pr_auc"],
            "precision": test_m["precision"],
            "recall": test_m["recall"],
            "f1_score": test_m["f1"],
            "brier": test_m["brier"],
            "positive_rate": test_m["positive_rate"],
            "train_samples": int(len(tr)),
            "val_samples": int(len(va)),
            "test_samples": int(len(te)),
        },
        "data_sources": {
            "labels_and_fire_history": "NASA FIRMS VIIRS NOAA-20 standard processing (SP), 2018-12..2025-12",
            "weather": (
                "ECMWF IFS HRES 9 km daily via Open-Meteo archive (temperature_2m_max, "
                "temperature_2m_mean, relative_humidity_2m_mean, wind_speed_10m_max, "
                "precipitation_sum; local day 19:00-19:00 UTC)"
            ),
            "districts": "GADM 4.1 India level 2 (676 districts)",
        },
        "fire_feature_source": args.fire_feature_source,
        "climatology": clim,
        "is_active": True,
    }
    (args.out_dir / f"{VERSION}_metadata.json").write_text(json.dumps(metadata, indent=2))
    (args.out_dir / "wildfire_v3_evaluation.json").write_text(json.dumps(evaluation, indent=2))
    print(
        json.dumps(
            {
                k: evaluation[k]
                for k in (
                    "validation",
                    "test",
                    "thresholds_from_validation",
                    "v2_vs_v3_same_2025_rows",
                )
                if k in evaluation
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
