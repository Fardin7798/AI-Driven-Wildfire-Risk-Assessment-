from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.v1.health import router as root_health_router
from app.api.v1.router import api_v1_router
from app.core.config import settings
from app.core.errors import register_exception_handlers
from app.core.logging import logger
from app.core.security import limiter
from app.jobs.scheduler import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "app_starting_up",
        version=settings.APP_VERSION,
        env=settings.ENV,
        scheduler=settings.ENABLE_SCHEDULER,
    )
    if settings.ENABLE_SCHEDULER:
        start_scheduler()
    yield
    logger.info("app_shutting_down")
    if settings.ENABLE_SCHEDULER:
        stop_scheduler()


def create_application() -> FastAPI:
    is_dev = settings.ENV == "development"

    application = FastAPI(
        title="AI-Driven Wildfire Risk Assessment & AQI Platform",
        description=(
            "Academic decision-support platform providing district-level wildfire risk assessment, "
            "active thermal anomaly tracking, and ambient air quality forecasting."
        ),
        version=settings.APP_VERSION,
        docs_url="/docs" if is_dev else None,
        redoc_url=None,
        openapi_url="/openapi.json" if is_dev else None,
        lifespan=lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    application.state.limiter = limiter
    application.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

    register_exception_handlers(application)

    application.include_router(api_v1_router, prefix="/api/v1")
    application.include_router(root_health_router)

    return application


app = create_application()
