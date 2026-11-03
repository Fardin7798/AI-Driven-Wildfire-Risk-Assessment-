import json
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter

from app.core.config import settings
from app.ml.loader import AQI_HORIZONS, model_loader
from app.schemas.models_info import ModelComparisonResponse, ModelVersionResponse

router = APIRouter(prefix="/models", tags=["Model Registry & Evaluation"])


def _aqi_model_entry() -> ModelVersionResponse:
    """AQI model B (no-station, CPCB PM2.5 sub-index at t+1..t+3). Metrics are the test MAE per
    horizon and the raw-CAMS reference on the same rows, read from the training run's
    aqi_station_evaluation.json; the test disclosure comes from aqi_station_metadata.json."""
    ver = settings.ACTIVE_AQI_MODEL
    model = model_loader.load_aqi_model(ver)
    if model is None:
        return ModelVersionResponse(
            model_type="aqi", version=ver, metrics=None, status="unavailable", is_active=False
        )
    trained = model.metadata.get("trained_at")
    metrics: dict[str, Any] | None = None
    eval_path = Path(settings.MODEL_DIR) / ver / "aqi_station_evaluation.json"
    try:
        ev = json.loads(eval_path.read_text(encoding="utf-8"))
        test = ev["test"]
        rows = {h: test[f"h{h}"]["all_rows_with_target"] for h in AQI_HORIZONS}
        metrics = {
            "target": "CPCB PM2.5 sub-index (24 h mean, IST day) at t+h",
            "variant": "no_station",
            "test_days": ev["protocol"]["test_days"],
            "test_mae": {f"h{h}": rows[h]["no_station"]["mae"] for h in AQI_HORIZONS},
            "raw_cams_mae": {f"h{h}": rows[h]["cams_t"]["mae"] for h in AQI_HORIZONS},
            "test_rows": {f"h{h}": rows[h]["no_station"]["n"] for h in AQI_HORIZONS},
            "test_disclosure": model.metadata.get("test_disclosure"),
        }
    except (OSError, ValueError, KeyError, TypeError):
        metrics = None
    return ModelVersionResponse(
        model_type="aqi",
        version=model.model_version,
        trained_at=datetime.fromisoformat(trained) if trained else None,
        metrics=metrics,
        status="active",
        feature_list=model.feature_list,
        thresholds={},
        is_active=True,
    )


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

    responses.append(_aqi_model_entry())
    return responses


@router.get("/comparison", response_model=ModelComparisonResponse)
async def get_model_comparison() -> ModelComparisonResponse:
    """Served wildfire model vs baselines on the held-out test year.

    Numbers come only from the evaluation file the training run wrote next to the artifact
    (`<model>_evaluation.json`); without it the endpoint says `not_available`.
    """
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
