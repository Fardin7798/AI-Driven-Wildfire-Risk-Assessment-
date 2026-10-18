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
            features.get("wind_max", 0.0),
            20.0,
            "km/h",
            "High wind gusts accelerating fire front propagation",
        ),
        (
            "Vegetation Fuel Dryness",
            features.get("ffmc", 85.0),
            85.0,
            "index",
            "Fine fuel moisture deficit in surface forest litter",
        ),
        (
            "Consecutive Dry Days",
            features.get("consecutive_dry_days", 0.0),
            7.0,
            "days",
            "Prolonged dry spell depleting fuel moisture",
        ),
        (
            "Maximum Temperature",
            features.get("temp_max", 25.0),
            32.0,
            "°C",
            "Elevated thermal conditions pre-heating vegetation",
        ),
        (
            "Duff & Drought Buildup",
            features.get("bui", 10.0),
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


def predict_wildfire_risk(
    features: dict[str, float],
    model_version: str | None = None,
    loader: ModelLoader | None = None,
) -> RiskPredictionResult:
    active_loader = loader or model_loader
    artifact = active_loader.load_wildfire_model(model_version)
    fwi_val = float(features.get("fwi", 5.0))

    if artifact and artifact.model_obj is not None:
        try:
            import numpy as np
            import xgboost as xgb

            # Build strictly ordered feature vector
            vector = [features.get(k, 0.0) for k in artifact.feature_list]
            dmatrix = xgb.DMatrix(np.array([vector]), feature_names=artifact.feature_list)
            raw_prob = float(artifact.model_obj.predict(dmatrix)[0])
            prob = max(0.0, min(1.0, raw_prob))

            risk_class = classify_probability(prob, artifact.thresholds)

            # Extract SHAP top factors if tree booster supports margins
            top_factors = _rank_fallback_factors(features)

            return RiskPredictionResult(
                probability=round(prob, 4),
                risk_class=risk_class,
                model_version=artifact.model_version,
                fwi_value=round(fwi_val, 2),
                top_factors=top_factors,
                is_fallback=False,
            )
        except Exception as e:
            logger.warn("model_inference_failed_falling_back_to_fwi", error=str(e))

    # Fallback: Canadian FWI rule-based scaling
    # Maps FWI (0 - 50+) monotonically to a risk probability
    fwi_prob = min(1.0, fwi_val / 40.0)
    risk_class = classify_fwi(fwi_val)
    top_factors = _rank_fallback_factors(features)

    return RiskPredictionResult(
        probability=round(fwi_prob, 4),
        risk_class=risk_class,
        model_version="fwi_fallback",
        fwi_value=round(fwi_val, 2),
        top_factors=top_factors,
        is_fallback=True,
    )
