"""Analytics router for AuditCaseOS dashboard statistics and trends."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.dependencies import get_cache
from app.routers.auth import get_current_user_required
from app.schemas.analytics import (
    CaseStatsResponse,
    DashboardOverview,
    EntityInsightsResponse,
    EvidenceFindingsStats,
    FullAnalyticsResponse,
    TrendsResponse,
    UserActivityResponse,
)
from app.services.analytics_service import analytics_service
from app.services.cache_service import CacheService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["analytics"])

# Type aliases for cleaner signatures
DbSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[dict, Depends(get_current_user_required)]
Cache = Annotated[CacheService, Depends(get_cache)]


@router.get("/overview", response_model=DashboardOverview)
async def get_overview(
    db: DbSession,
    current_user: CurrentUser,
    cache: Cache,
) -> DashboardOverview:
    """
    Get dashboard overview statistics.

    Returns counts for total cases, open/in-progress/closed cases,
    critical cases, evidence, findings, entities, and average resolution time.

    Results are cached for 10 minutes.
    """
    settings = get_settings()

    async def compute():
        return await analytics_service.get_dashboard_overview(db)

    result = await cache.get_or_compute(
        key="cache:analytics:overview",
        compute_func=compute,
        ttl=settings.cache_analytics_ttl,
    )
    return DashboardOverview(**result) if isinstance(result, dict) else result


@router.get("/cases", response_model=CaseStatsResponse)
async def get_case_stats(
    db: DbSession,
    current_user: CurrentUser,
    cache: Cache,
    scope: str | None = Query(None, description="Filter by scope code"),
) -> CaseStatsResponse:
    """
    Get case statistics breakdown.

    Returns case counts by status, severity, type, and scope.
    Optionally filter by scope code.

    Results are cached for 20 minutes (keyed by scope).
    """
    settings = get_settings()
    cache_key = f"cache:analytics:cases:{scope or 'all'}"

    async def compute():
        return await analytics_service.get_case_stats(db, scope_code=scope)

    result = await cache.get_or_compute(
        key=cache_key,
        compute_func=compute,
        ttl=settings.cache_analytics_ttl * 2,  # 20 minutes
    )
    return CaseStatsResponse(**result) if isinstance(result, dict) else result


@router.get("/trends", response_model=TrendsResponse)
async def get_trends(
    db: DbSession,
    current_user: CurrentUser,
    cache: Cache,
    days: int = Query(30, ge=7, le=365, description="Number of days to analyze"),
    granularity: str = Query(
        "day",
        regex="^(day|week|month)$",
        description="Time granularity (day, week, month)",
    ),
) -> TrendsResponse:
    """
    Get case creation and closure trends over time.

    Returns daily/weekly/monthly counts of cases created and closed.

    Results are cached for 30 minutes (keyed by days and granularity).
    """
    settings = get_settings()
    cache_key = f"cache:analytics:trends:{days}:{granularity}"

    async def compute():
        return await analytics_service.get_case_trends(db, days=days, granularity=granularity)

    result = await cache.get_or_compute(
        key=cache_key,
        compute_func=compute,
        ttl=settings.cache_analytics_ttl * 3,  # 30 minutes
    )
    return TrendsResponse(**result) if isinstance(result, dict) else result


@router.get("/evidence-findings", response_model=EvidenceFindingsStats)
async def get_evidence_findings_stats(
    db: DbSession,
    current_user: CurrentUser,
    cache: Cache,
) -> EvidenceFindingsStats:
    """
    Get evidence and findings statistics.

    Returns evidence breakdown by type and findings breakdown by severity.

    Results are cached for 10 minutes.
    """
    settings = get_settings()

    async def compute():
        return await analytics_service.get_evidence_findings_stats(db)

    result = await cache.get_or_compute(
        key="cache:analytics:evidence-findings",
        compute_func=compute,
        ttl=settings.cache_analytics_ttl,
    )
    return EvidenceFindingsStats(**result) if isinstance(result, dict) else result


@router.get("/entities", response_model=EntityInsightsResponse)
async def get_entity_insights(
    db: DbSession,
    current_user: CurrentUser,
    cache: Cache,
    entity_type: str | None = Query(None, description="Filter by entity type"),
    limit: int = Query(10, ge=1, le=50, description="Max number of top entities"),
) -> EntityInsightsResponse:
    """
    Get entity extraction insights.

    Returns entity type distribution and top occurring entities.

    Results are cached for 10 minutes (keyed by entity_type and limit).
    """
    settings = get_settings()
    cache_key = f"cache:analytics:entities:{entity_type or 'all'}:{limit}"

    async def compute():
        return await analytics_service.get_entity_insights(
            db, entity_type=entity_type, limit=limit
        )

    result = await cache.get_or_compute(
        key=cache_key,
        compute_func=compute,
        ttl=settings.cache_analytics_ttl,
    )
    return EntityInsightsResponse(**result) if isinstance(result, dict) else result


@router.get("/activity", response_model=UserActivityResponse)
async def get_user_activity(
    db: DbSession,
    current_user: CurrentUser,
    cache: Cache,
    days: int = Query(30, ge=1, le=90, description="Number of days to analyze"),
    limit: int = Query(10, ge=1, le=50, description="Max number of top users"),
) -> UserActivityResponse:
    """
    Get user activity metrics from audit log.

    Returns activity breakdown by action type and top active users.

    Results are cached for 10 minutes (keyed by days and limit).
    """
    settings = get_settings()
    cache_key = f"cache:analytics:activity:{days}:{limit}"

    async def compute():
        return await analytics_service.get_user_activity(db, days=days, limit=limit)

    result = await cache.get_or_compute(
        key=cache_key,
        compute_func=compute,
        ttl=settings.cache_analytics_ttl,
    )
    return UserActivityResponse(**result) if isinstance(result, dict) else result


@router.get("/full", response_model=FullAnalyticsResponse)
async def get_full_analytics(
    db: DbSession,
    current_user: CurrentUser,
    cache: Cache,
    days: int = Query(30, ge=7, le=365, description="Number of days for trends"),
) -> FullAnalyticsResponse:
    """
    Get complete analytics data for dashboard.

    Returns all analytics in a single response: overview, case stats,
    trends, evidence/findings stats, entity insights, and user activity.

    Results are cached for 15 minutes (keyed by days).
    """
    settings = get_settings()
    cache_key = f"cache:analytics:full:{days}"

    async def compute():
        return await analytics_service.get_full_analytics(db, days=days)

    result = await cache.get_or_compute(
        key=cache_key,
        compute_func=compute,
        ttl=int(settings.cache_analytics_ttl * 1.5),  # 15 minutes
    )
    return FullAnalyticsResponse(**result) if isinstance(result, dict) else result
