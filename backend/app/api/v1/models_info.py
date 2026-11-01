from datetime import datetime

from fastapi import APIRouter

from app.ml.loader import model_loader
from app.schemas.models_info import ModelComparisonResponse, ModelVersionResponse

router = APIRouter(prefix="/models", tags=["Model Registry & Evaluation"])


@router.get("/current", response_model=list[ModelVersionResponse])
async def get_active_models() -> list[ModelVersionResponse]:
    """Models that ACTUALLY serve predictions right now, read from the deployed artifacts.

    The answer comes from the files the predictor loads (not from a DB row someone typed), so it
    cannot drift from what the API is really doing.
    """
    responses: list[ModelVersionResponse] = []

    wf = model_loader.load_wildfire_model()
    if wf and wf.model_obj is not None:
        trained = wf.metadata.get("trained_at")
        responses.append(
            ModelVersionResponse(
                model_type="wildfire",
                version=wf.model_version,
                trained_at=datetime.fromisoformat(trained) if trained else None,
                metrics=wf.metrics,
                status="active",
                feature_list=wf.feature_list,
                thresholds=wf.thresholds,
                is_active=True,
            )
        )
    else:
        responses.append(
            ModelVersionResponse(
                model_type="wildfire",
                version="fwi_fallback",
                metrics=None,
                status="fallback_rule_based",
                feature_list=["fwi"],
                thresholds={},
                is_active=True,
            )
        )

    # AQI forecasts are produced by the rule-based persistence + dispersion forecaster
    # (app/ml/aqi_forecaster.py). No learned AQI model is served, so no metrics are claimed.
    responses.append(
        ModelVersionResponse(
            model_type="aqi",
            version="aqi_persistence_v1",
            metrics=None,
            status="rule_based_not_validated",
            feature_list=["current_aqi", "pm25", "pm10", "wind_max", "precip_sum"],
            thresholds={},
            is_active=True,
        )
    )
    return responses


@router.get("/comparison", response_model=ModelComparisonResponse)
async def get_model_comparison() -> ModelComparisonResponse:
    """Benchmark operational models against baseline algorithms across standardized metrics."""
    import json
    from pathlib import Path

    paths = [
        Path("ml/reports/model_comparison.json"),
        Path(__file__).resolve().parents[4] / "ml" / "reports" / "model_comparison.json",
        Path(__file__).resolve().parents[3] / "ml" / "reports" / "model_comparison.json",
    ]
    for p in paths:
        if p.exists():
            try:
                with open(p, encoding="utf-8") as f:
                    data = json.load(f)
                    return ModelComparisonResponse(
                        status="available",
                        models=data.get("models", []),
                        wildfire_comparison=data.get("wildfire_comparison"),
                        aqi_comparison=data.get("aqi_comparison"),
                        evaluation_criteria=data.get("evaluation_criteria", []),
                    )
            except Exception:
                pass

    return ModelComparisonResponse(
        status="not_available",
        models=[],
        wildfire_comparison=None,
        aqi_comparison=None,
        evaluation_criteria=[],
    )
