from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.db.models.model_registry import ModelVersion
from app.schemas.models_info import ModelComparisonResponse, ModelVersionResponse

router = APIRouter(prefix="/models", tags=["Model Registry & Evaluation"])


@router.get("/current", response_model=list[ModelVersionResponse])
async def get_active_models(
    db: AsyncSession = Depends(get_db),
) -> list[ModelVersionResponse]:
    """Retrieve operational ML models actively serving predictions and forecasts."""
    try:
        query = select(ModelVersion).where(ModelVersion.is_active.is_(True))
        result = await db.execute(query)
        records = list(result.scalars().all())
    except Exception:
        records = []

    if not records:
        return [
            ModelVersionResponse(
                id=None,
                model_type="wildfire",
                version="fwi_fallback",
                trained_at=None,
                metrics=None,
                status="awaiting_training",
                feature_list=[],
                thresholds={"moderate": 0.35, "high": 0.60, "extreme": 0.80},
                is_active=True,
            ),
            ModelVersionResponse(
                id=None,
                model_type="aqi",
                version="aqi_persistence",
                trained_at=None,
                metrics=None,
                status="awaiting_training",
                feature_list=[],
                thresholds={},
                is_active=True,
            ),
        ]

    responses: list[ModelVersionResponse] = []
    for r in records:
        f_list: list[str] = (
            list(r.feature_list.keys())
            if isinstance(r.feature_list, dict)
            else list(r.feature_list)
        )
        responses.append(
            ModelVersionResponse(
                id=r.id,
                model_type=r.model_type,
                version=r.version,
                trained_at=r.trained_at,
                metrics=r.metrics,
                feature_list=f_list,
                thresholds=r.thresholds,
                is_active=r.is_active,
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
