"""
Health check router for AuditCaseOS API.

Provides endpoints for monitoring service health and readiness.
"""

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.dependencies import get_cache
from app.services.cache_service import CacheService

router = APIRouter()
settings = get_settings()


@router.get("/ready")
async def readiness_check(
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache),
) -> dict[str, Any]:
    """
    Readiness check endpoint.

    Verifies that all critical dependencies are available and the service
    is ready to accept traffic.

    Args:
        db: Database session for connectivity check.
        cache: Cache service for Redis connectivity check.

    Returns:
        dict: Readiness status with component health details.
    """
    checks: dict[str, str] = {}

    # Check database connectivity (via PgBouncer if enabled)
    try:
        await db.execute(text("SELECT 1"))
        if settings.pgbouncer_enabled:
            checks["database"] = "healthy (via pgbouncer)"
        else:
            checks["database"] = "healthy (direct)"
    except Exception as e:
        checks["database"] = f"unhealthy: {e!s}"

    # Check Redis cache connectivity (non-critical)
    try:
        if settings.redis_enabled:
            if await cache.ping():
                checks["cache"] = "healthy"
            else:
                checks["cache"] = "unavailable (degraded mode)"
        else:
            checks["cache"] = "disabled"
    except Exception as e:
        checks["cache"] = f"unavailable: {e!s}"

    # Overall status - database is critical, cache is optional
    db_healthy = "healthy" in checks.get("database", "")
    overall_status = "ready" if db_healthy else "not_ready"

    return {
        "status": overall_status,
        "checks": checks,
        "connection_mode": "pgbouncer" if settings.pgbouncer_enabled else "direct",
        "cache_enabled": settings.redis_enabled,
    }
