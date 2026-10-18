from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

db_url = settings.DATABASE_URL
if db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

# Configure async engine with connection pooling
connect_args: dict[str, Any] = {}
if ":6543" in db_url:
    connect_args["statement_cache_size"] = 0
if "localhost" not in db_url and "127.0.0.1" not in db_url:
    connect_args["ssl"] = "require"
elif "sslmode=require" in db_url or "ssl=require" in db_url:
    connect_args["ssl"] = "require"

engine = create_async_engine(
    db_url,
    echo=(settings.ENV == "development" and settings.LOG_LEVEL.upper() == "DEBUG"),
    pool_pre_ping=True,
    pool_size=3,
    max_overflow=2,
    pool_recycle=300,
    connect_args=connect_args,
)

async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
