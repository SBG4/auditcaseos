"""Analytics router for AuditCaseOS dashboard statistics and trends."""

import logging
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
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

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["analytics"])

# Type aliases for cleaner signatures
DbSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[dict, Depends(get_current_user_required)]


@router.get("/overview", response_model=DashboardOverview)
async def get_overview(
    db: DbSession,
    current_user: CurrentUser,
) -> DashboardOverview:
    """
    Get dashboard overview statistics.

    Returns counts for total cases, open/in-progress/closed cases,
    critical cases, evidence, findings, entities, and average resolution time.
    """
    return await analytics_service.get_dashboard_overview(db)


@router.get("/cases", response_model=CaseStatsResponse)
async def get_case_stats(
    db: DbSession,
    current_user: CurrentUser,
    scope: Optional[str] = Query(None, description="Filter by scope code"),
) -> CaseStatsResponse:
    """
    Get case statistics breakdown.

    Returns case counts by status, severity, type, and scope.
    Optionally filter by scope code.
    """
    return await analytics_service.get_case_stats(db, scope_code=scope)


@router.get("/trends", response_model=TrendsResponse)
async def get_trends(
    db: DbSession,
    current_user: CurrentUser,
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
    """
    return await analytics_service.get_case_trends(db, days=days, granularity=granularity)


@router.get("/evidence-findings", response_model=EvidenceFindingsStats)
async def get_evidence_findings_stats(
    db: DbSession,
    current_user: CurrentUser,
) -> EvidenceFindingsStats:
    """
    Get evidence and findings statistics.

    Returns evidence breakdown by type and findings breakdown by severity.
    """
    return await analytics_service.get_evidence_findings_stats(db)


@router.get("/entities", response_model=EntityInsightsResponse)
async def get_entity_insights(
    db: DbSession,
    current_user: CurrentUser,
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    limit: int = Query(10, ge=1, le=50, description="Max number of top entities"),
) -> EntityInsightsResponse:
    """
    Get entity extraction insights.

    Returns entity type distribution and top occurring entities.
    """
    return await analytics_service.get_entity_insights(
        db, entity_type=entity_type, limit=limit
    )


@router.get("/activity", response_model=UserActivityResponse)
async def get_user_activity(
    db: DbSession,
    current_user: CurrentUser,
    days: int = Query(30, ge=1, le=90, description="Number of days to analyze"),
    limit: int = Query(10, ge=1, le=50, description="Max number of top users"),
) -> UserActivityResponse:
    """
    Get user activity metrics from audit log.

    Returns activity breakdown by action type and top active users.
    """
    return await analytics_service.get_user_activity(db, days=days, limit=limit)


@router.get("/full", response_model=FullAnalyticsResponse)
async def get_full_analytics(
    db: DbSession,
    current_user: CurrentUser,
    days: int = Query(30, ge=7, le=365, description="Number of days for trends"),
) -> FullAnalyticsResponse:
    """
    Get complete analytics data for dashboard.

    Returns all analytics in a single response: overview, case stats,
    trends, evidence/findings stats, entity insights, and user activity.
    """
    return await analytics_service.get_full_analytics(db, days=days)
