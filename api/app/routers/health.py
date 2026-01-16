"""
Health check router for AuditCaseOS API.

Provides endpoints for monitoring service health and readiness.
"""

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db

router = APIRouter()


@router.get("/ready")
async def readiness_check(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """
    Readiness check endpoint.

    Verifies that all critical dependencies are available and the service
    is ready to accept traffic.

    Args:
        db: Database session for connectivity check.

    Returns:
        dict: Readiness status with component health details.
    """
    checks: dict[str, str] = {}

    # Check database connectivity
    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = "healthy"
    except Exception as e:
        checks["database"] = f"unhealthy: {e!s}"

    overall_status = "ready" if all(
        v == "healthy" for v in checks.values()
    ) else "not_ready"

    return {
        "status": overall_status,
        "checks": checks,
    }
