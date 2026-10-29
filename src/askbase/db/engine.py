"""Database engine lifecycle and connectivity checks."""

import time
from typing import Any

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    create_async_engine,
)

from askbase.core.logging import get_logger
from askbase.core.settings import get_settings

logger = get_logger(__name__)

_engine: AsyncEngine | None = None


def get_engine(database_url: str | None = None) -> AsyncEngine:
    """Get or create singleton AsyncEngine."""
    global _engine
    if _engine is not None:
        return _engine

    settings = get_settings()
    url = database_url or settings.DATABASE_URL

    kwargs: dict[str, Any] = {
        "echo": settings.DATABASE_ECHO,
    }

    if url.startswith("sqlite"):
        # SQLite specific options
        kwargs["connect_args"] = {"check_same_thread": False}
        _engine = create_async_engine(url, **kwargs)

        # Enforce foreign key constraints in SQLite
        @event.listens_for(_engine.sync_engine, "connect")
        def set_sqlite_pragma(dbapi_connection: Any, _connection_record: Any) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
    else:
        # PostgreSQL with asyncpg connection pooling
        kwargs.update(
            {
                "pool_size": settings.DATABASE_POOL_MIN,
                "max_overflow": settings.DATABASE_POOL_MAX - settings.DATABASE_POOL_MIN,
                "pool_pre_ping": True,
            }
        )
        _engine = create_async_engine(url, **kwargs)

    return _engine


async def close_engine() -> None:
    """Dispose database connection pool gracefully."""
    global _engine
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        logger.info("Database engine disposed.")


async def check_db_connectivity() -> dict[str, Any]:
    """Execute a lightweight ping query (SELECT 1) to determine DB health."""
    start = time.perf_counter()
    try:
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        return {
            "connected": True,
            "latency_ms": latency_ms,
            "error": None,
        }
    except Exception as e:
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.warning(f"Database connectivity check failed: {e}")
        return {
            "connected": False,
            "latency_ms": latency_ms,
            "error": str(e),
        }
