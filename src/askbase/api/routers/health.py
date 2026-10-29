"""Health and readiness probes."""

import time
from datetime import UTC, datetime

from fastapi import APIRouter, Response

from askbase.api.deps import DBSession

router = APIRouter(tags=["Health"])

_process_start_time = time.time()


@router.get("/")
async def root():
    """Root operational metadata."""
    return {
        "name": "AskBase API",
        "version": "0.2.0",
        "status": "operational",
    }


@router.get("/health/live")
@router.get("/health")
async def liveness_probe():
    """Process liveness probe indicating application process responsiveness."""
    uptime = round(time.time() - _process_start_time, 2)
    return {
        "status": "ok",
        "uptime": uptime,
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.get("/health/ready")
@router.get("/ready")
async def readiness_probe(response: Response, db: DBSession):
    """Dependency readiness probe testing database connectivity.

    Returns 200 OK when connected or 503 Service Unavailable when degraded.
    """
    timestamp = datetime.now(UTC).isoformat()
    start = time.perf_counter()
    try:
        from sqlalchemy import text

        await db.execute(text("SELECT 1"))
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        return {
            "status": "ok",
            "database": {
                "status": "connected",
                "latencyMs": latency_ms,
            },
            "timestamp": timestamp,
        }
    except Exception as e:
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        response.status_code = 503
        return {
            "status": "degraded",
            "database": {
                "status": "disconnected",
                "error": str(e) or "Database ping failed",
            },
            "timestamp": timestamp,
        }
