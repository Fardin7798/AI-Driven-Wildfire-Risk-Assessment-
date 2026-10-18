from fastapi import Header, HTTPException, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings

limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])


async def verify_job_token(x_job_token: str = Header(..., alias="X-Job-Token")) -> bool:
    if not settings.JOB_TOKEN or x_job_token != settings.JOB_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or unauthorized X-Job-Token header.",
        )
    return True
