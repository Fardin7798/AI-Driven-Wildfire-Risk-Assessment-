"""Train wildfire_xgb_v2 (district x day fire-occurrence model) and evaluate it honestly.

Reads the table from ml/pipeline/build_wildfire_dataset.py. Chronological split:
train <= 2022, validation 2023 (early stopping + thresholds), test 2024 (reported once).

Baselines are computed here, on the same test rows, never typed in:
  * fwi_only       - probability = FWI value (ranking only)
  * climatology    - district-month historical fire-day rate (train years)
  * persistence    - fires_prev_7d (any detection in the previous 7 days)

Writes to --out-dir:
  wildfire_xgb_v2.json              XGBoost booster
  wildfire_xgb_v2_metadata.json     features, thresholds, metrics, sha256, climatology
  wildfire_v2_evaluation.json       full metrics for model + baselines (val and test)
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

VERSION = "wildfire_xgb_v2"


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


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--dataset", type=Path, required=True)
    ap.add_argument("--climatology", type=Path, required=True)
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--fire-feature-source", default="VIIRS_NOAA20_NRT")
    args = ap.parse_args()

    df = pd.read_parquet(args.dataset)
    feats = WILDFIRE_V2_FEATURES
    missing = [c for c in feats + ["label", "split"] if c not in df.columns]
    if missing:
        raise SystemExit(f"dataset missing columns: {missing}")
    if df[feats].isna().any().any():
        bad = df[feats].isna().sum()
        raise SystemExit(f"NaN features in dataset:\n{bad[bad > 0]}")

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

    y_va, y_te = va.label.values, te.label.values
    evaluation = {
        "model": VERSION,
        "split": {"train": "2019-2022", "validation": "2023", "test": "2024"},
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
            "test_year": 2024,
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
            "labels_and_fire_history": "NASA FIRMS VIIRS NOAA-20 standard processing (SP), 2019-2024",
            "weather": "NASA POWER daily (T2M_MAX, T2M, RH2M, WS10M_MAX, PRECTOTCORR)",
            "districts": "GADM 4.1 India level 2 (676 districts)",
        },
        "fire_feature_source": args.fire_feature_source,
        "climatology": clim,
        "is_active": True,
    }
    (args.out_dir / f"{VERSION}_metadata.json").write_text(json.dumps(metadata, indent=2))
    (args.out_dir / "wildfire_v2_evaluation.json").write_text(json.dumps(evaluation, indent=2))
    print(
        json.dumps(
            {k: evaluation[k] for k in ("validation", "test", "thresholds_from_validation")},
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
