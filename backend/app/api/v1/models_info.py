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

    # AQI forecasts are the persistence baseline (app/ml/aqi_forecaster.py): the latest observed
    # AQI repeated for days +1..+3. No learned AQI model is served, so no metrics are claimed.
    responses.append(
        ModelVersionResponse(
            model_type="aqi",
            version="aqi_persistence_v1",
            metrics=None,
            status="persistence_baseline",
            feature_list=["observed_aqi"],
            thresholds={},
            is_active=True,
        )
    )
    return responses


@router.get("/comparison", response_model=ModelComparisonResponse)
async def get_model_comparison() -> ModelComparisonResponse:
    """Served wildfire model vs baselines on the held-out test year.

    Numbers come only from the evaluation file the training run wrote next to the artifact
    (`<model>_evaluation.json`); without it the endpoint says `not_available`.
    """
    import json
    from pathlib import Path

    from app.core.config import settings

    path = Path(settings.MODEL_DIR) / f"{settings.ACTIVE_WILDFIRE_MODEL}_evaluation.json"
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            test = data["test"]
            return ModelComparisonResponse(
                status="available",
                models=[{"name": name, **metrics} for name, metrics in test.items()],
                wildfire_comparison={
                    "model": data.get("model"),
                    "split": data.get("split"),
                    "label": data.get("label"),
                    "thresholds": data.get("thresholds_from_validation"),
                    "test": test,
                    "validation": data.get("validation"),
                    "feature_importance_gain": data.get("feature_importance_gain"),
                },
                aqi_comparison=None,
                evaluation_criteria=["roc_auc", "pr_auc", "precision", "recall", "f1", "brier"],
            )
        except (OSError, ValueError, KeyError):
            pass

    return ModelComparisonResponse(
        status="not_available",
        models=[],
        wildfire_comparison=None,
        aqi_comparison=None,
        evaluation_criteria=[],
    )
