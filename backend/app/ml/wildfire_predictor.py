import math
from dataclasses import dataclass
from typing import Any

from app.core.logging import logger
from app.domain.risk_classes import classify_fwi, classify_probability
from app.ml.loader import ModelLoader, model_loader


@dataclass(frozen=True)
class RiskPredictionResult:
    probability: float
    risk_class: str
    model_version: str
    fwi_value: float
    top_factors: dict[str, Any]
    is_fallback: bool


def _rank_fallback_factors(features: dict[str, float]) -> dict[str, Any]:
    """Identify top 3 primary environmental drivers when operating in FWI baseline fallback mode."""
    candidates = [
        (
            "Wind Velocity",
            features.get("wind_max") or 0.0,
            20.0,
            "km/h",
            "High wind gusts accelerating fire front propagation",
        ),
        (
            "Vegetation Fuel Dryness",
            features.get("ffmc") or 0.0,
            85.0,
            "index",
            "Fine fuel moisture deficit in surface forest litter",
        ),
        (
            "Consecutive Dry Days",
            features.get("consecutive_dry_days") or 0.0,
            7.0,
            "days",
            "Prolonged dry spell depleting fuel moisture",
        ),
        (
            "Maximum Temperature",
            features.get("temp_max") or 0.0,
            32.0,
            "°C",
            "Elevated thermal conditions pre-heating vegetation",
        ),
        (
            "Duff & Drought Buildup",
            features.get("bui") or 0.0,
            20.0,
            "index",
            "Sub-surface duff and organic fuel accumulation",
        ),
    ]

    scored = []
    for label, val, threshold, unit, desc in candidates:
        severity = val / threshold if threshold > 0 else 0.0
        scored.append((severity, label, val, unit, desc))

    scored.sort(key=lambda x: x[0], reverse=True)
    top_3 = scored[:3]

    return {
        "factors": [
            {"factor": label, "value": round(val, 1), "unit": unit, "description": desc}
            for _, label, val, unit, desc in top_3
        ]
    }


FEATURE_LABELS: dict[str, str] = {
    "temp_max": "Maximum Temperature",
    "temp_mean": "Mean Temperature",
    "rh_mean": "Relative Humidity",
    "wind_max": "Wind Velocity",
    "precip_sum": "Rainfall Today",
    "precip_sum_3d": "Rainfall (3 days)",
    "precip_sum_7d": "Rainfall (7 days)",
    "precip_sum_14d": "Rainfall (14 days)",
    "precip_sum_30d": "Rainfall (30 days)",
    "temp_max_mean_7d": "Max Temperature (7-day mean)",
    "consecutive_dry_days": "Consecutive Dry Days",
    "days_since_rain_gt_10mm": "Days Since Heavy Rain",
    "ffmc": "Fine Fuel Moisture Code",
    "dmc": "Duff Moisture Code",
    "dc": "Drought Code",
    "isi": "Initial Spread Index",
    "bui": "Buildup Index",
    "fwi": "Fire Weather Index",
    "fires_prev_7d": "Fires in Last 7 Days",
    "fires_prev_30d": "Fires in Last 30 Days",
    "climatological_fire_freq": "Historical Fire Frequency (this month)",
}


def missing_features(features: dict[str, float], required: list[str]) -> list[str]:
    """Names of required features that are absent, None or NaN."""
    out = []
    for k in required:
        v = features.get(k)
        if v is None or (isinstance(v, float) and math.isnan(v)):
            out.append(k)
    return out


def _shap_top_factors(
    booster: Any, dmatrix: Any, feature_list: list[str], features: dict[str, float]
) -> dict[str, Any]:
    """Top 3 features pushing risk UP for this row, from XGBoost's exact TreeSHAP contributions."""
    contribs = booster.predict(dmatrix, pred_contribs=True)[0][:-1]  # last column = bias
    ranked = sorted(zip(feature_list, contribs, strict=True), key=lambda x: x[1], reverse=True)
    factors = []
    for name, contrib in ranked:
        if name in ("lat", "lon") or name.endswith(("_sin", "_cos")) or contrib <= 0:
            continue
        factors.append(
            {
                "factor": FEATURE_LABELS.get(name, name),
                "feature": name,
                "value": round(float(features[name]), 3),
                "shap_contribution": round(float(contrib), 4),
            }
        )
        if len(factors) == 3:
            break
    return {"method": "xgboost_treeshap", "factors": factors}


def predict_wildfire_risk(
    features: dict[str, float],
    model_version: str | None = None,
    loader: ModelLoader | None = None,
) -> RiskPredictionResult | None:
    """Score one district-day.

    Returns None when even the FWI fallback cannot be computed (no FWI for the day): callers
    must then skip the region instead of publishing an invented risk.
    """
    active_loader = loader or model_loader
    artifact = active_loader.load_wildfire_model(model_version)
    fwi_raw = features.get("fwi")
    fwi_val = None if fwi_raw is None or math.isnan(float(fwi_raw)) else float(fwi_raw)

    if artifact and artifact.model_obj is not None:
        missing = missing_features(features, artifact.feature_list)
        if missing:
            logger.warn(
                "model_features_missing_falling_back_to_fwi",
                model=artifact.model_version,
                missing=missing,
            )
        else:
            try:
                import numpy as np
                import xgboost as xgb

                vector = [float(features[k]) for k in artifact.feature_list]
                dmatrix = xgb.DMatrix(np.array([vector]), feature_names=artifact.feature_list)
                prob = max(0.0, min(1.0, float(artifact.model_obj.predict(dmatrix)[0])))
                return RiskPredictionResult(
                    probability=round(prob, 4),
                    risk_class=classify_probability(prob, artifact.thresholds),
                    model_version=artifact.model_version,
                    fwi_value=round(fwi_val, 2) if fwi_val is not None else float("nan"),
                    top_factors=_shap_top_factors(
                        artifact.model_obj, dmatrix, artifact.feature_list, features
                    ),
                    is_fallback=False,
                )
            except Exception as e:
                logger.warn("model_inference_failed_falling_back_to_fwi", error=str(e))

    if fwi_val is None:
        return None

    # Fallback: Canadian FWI danger classes (no learned probability).
    # The probability is a monotone rescaling of FWI for map colouring only.
    return RiskPredictionResult(
        probability=round(min(1.0, fwi_val / 40.0), 4),
        risk_class=classify_fwi(fwi_val),
        model_version="fwi_fallback",
        fwi_value=round(fwi_val, 2),
        top_factors=_rank_fallback_factors(features),
        is_fallback=True,
    )
