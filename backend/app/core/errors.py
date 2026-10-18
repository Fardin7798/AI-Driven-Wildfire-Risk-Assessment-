from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.core.logging import logger


class ProblemDetails(BaseModel):
    type: str = "about:blank"
    title: str
    status: int
    detail: str
    instance: str | None = None
    extra: dict[str, Any] | None = None


class AppException(Exception):
    def __init__(
        self,
        title: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail: str = "An internal server error occurred.",
        type_: str = "about:blank",
        extra: dict[str, Any] | None = None,
    ):
        super().__init__(detail)
        self.title = title
        self.status_code = status_code
        self.detail = detail
        self.type_ = type_
        self.extra = extra


class NotFoundException(AppException):
    def __init__(
        self, detail: str = "The requested resource was not found.", title: str = "Not Found"
    ):
        super().__init__(
            title=title,
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
            type_="https://errors.wildfire.org/not-found",
        )


class UnauthorizedJobTokenException(AppException):
    def __init__(self, detail: str = "Invalid or missing X-Job-Token header."):
        super().__init__(
            title="Unauthorized",
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            type_="https://errors.wildfire.org/unauthorized",
        )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        logger.warn("app_exception", title=exc.title, status=exc.status_code, path=request.url.path)
        problem = ProblemDetails(
            type=exc.type_,
            title=exc.title,
            status=exc.status_code,
            detail=exc.detail,
            instance=request.url.path,
            extra=exc.extra,
        )
        return JSONResponse(
            status_code=exc.status_code, content=problem.model_dump(exclude_none=True)
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        logger.warn("validation_error", errors=exc.errors(), path=request.url.path)
        problem = ProblemDetails(
            type="https://errors.wildfire.org/validation-error",
            title="Unprocessable Entity",
            status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The request failed validation checks.",
            instance=request.url.path,
            extra={"errors": exc.errors()},
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=problem.model_dump(exclude_none=True),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.error("unhandled_exception", error=str(exc), path=request.url.path, exc_info=True)
        problem = ProblemDetails(
            type="https://errors.wildfire.org/internal-error",
            title="Internal Server Error",
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again later.",
            instance=request.url.path,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=problem.model_dump(exclude_none=True),
        )
