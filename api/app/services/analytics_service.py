"""Analytics service for dashboard statistics and trends."""

import logging
from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.analytics import (
    ActionCount,
    CaseStatsResponse,
    DashboardOverview,
    EntityInsightsResponse,
    EntityTypeStats,
    EvidenceFindingsStats,
    FullAnalyticsResponse,
    ScopeCount,
    SeverityCount,
    StatusCount,
    TopEntity,
    TrendDataPoint,
    TrendsResponse,
    TypeCount,
    UserActivityResponse,
    UserActivityStat,
)

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Service for analytics and statistics aggregation."""

    async def get_dashboard_overview(self, db: AsyncSession) -> DashboardOverview:
        """Get overview statistics for dashboard cards."""
        try:
            query = text("""
                SELECT
                    (SELECT COUNT(*) FROM cases) as total_cases,
                    (SELECT COUNT(*) FROM cases WHERE status = 'OPEN') as open_cases,
                    (SELECT COUNT(*) FROM cases WHERE status = 'IN_PROGRESS') as in_progress_cases,
                    (SELECT COUNT(*) FROM cases WHERE status = 'CLOSED') as closed_cases,
                    (SELECT COUNT(*) FROM cases WHERE severity = 'CRITICAL' AND status != 'CLOSED') as critical_cases,
                    (SELECT COUNT(*) FROM cases WHERE severity = 'HIGH' AND status != 'CLOSED') as high_severity_cases,
                    (SELECT COUNT(*) FROM evidence) as total_evidence,
                    (SELECT COUNT(*) FROM findings) as total_findings,
                    (SELECT COUNT(*) FROM case_entities) as total_entities,
                    (SELECT AVG(EXTRACT(EPOCH FROM (closed_at - created_at)) / 86400)
                     FROM cases WHERE closed_at IS NOT NULL) as avg_resolution_days
            """)
            result = await db.execute(query)
            row = result.fetchone()

            return DashboardOverview(
                total_cases=row[0] or 0,
                open_cases=row[1] or 0,
                in_progress_cases=row[2] or 0,
                closed_cases=row[3] or 0,
                critical_cases=row[4] or 0,
                high_severity_cases=row[5] or 0,
                total_evidence=row[6] or 0,
                total_findings=row[7] or 0,
                total_entities=row[8] or 0,
                avg_resolution_days=round(row[9], 1) if row[9] else None,
            )
        except Exception as e:
            logger.error(f"Failed to get dashboard overview: {e}")
            raise

    async def get_case_stats(
        self, db: AsyncSession, scope_code: Optional[str] = None
    ) -> CaseStatsResponse:
        """Get case statistics by status, severity, type, and scope."""
        try:
            scope_filter = "WHERE scope_code = :scope_code" if scope_code else ""
            params = {"scope_code": scope_code} if scope_code else {}

            # Get total count
            total_query = text(f"SELECT COUNT(*) FROM cases {scope_filter}")
            total_result = await db.execute(total_query, params)
            total = total_result.scalar() or 0

            # Status breakdown
            status_query = text(f"""
                SELECT status::text, COUNT(*) as count
                FROM cases {scope_filter}
                GROUP BY status
                ORDER BY count DESC
            """)
            status_result = await db.execute(status_query, params)
            by_status = [
                StatusCount(
                    status=row[0],
                    count=row[1],
                    percentage=round((row[1] / total * 100) if total > 0 else 0, 1),
                )
                for row in status_result.fetchall()
            ]

            # Severity breakdown
            severity_query = text(f"""
                SELECT severity::text, COUNT(*) as count
                FROM cases {scope_filter}
                GROUP BY severity
                ORDER BY
                    CASE severity
                        WHEN 'CRITICAL' THEN 1
                        WHEN 'HIGH' THEN 2
                        WHEN 'MEDIUM' THEN 3
                        WHEN 'LOW' THEN 4
                    END
            """)
            severity_result = await db.execute(severity_query, params)
            by_severity = [
                SeverityCount(
                    severity=row[0],
                    count=row[1],
                    percentage=round((row[1] / total * 100) if total > 0 else 0, 1),
                )
                for row in severity_result.fetchall()
            ]

            # Type breakdown
            type_query = text(f"""
                SELECT case_type::text, COUNT(*) as count
                FROM cases {scope_filter}
                GROUP BY case_type
                ORDER BY count DESC
            """)
            type_result = await db.execute(type_query, params)
            by_type = [
                TypeCount(
                    type=row[0],
                    count=row[1],
                    percentage=round((row[1] / total * 100) if total > 0 else 0, 1),
                )
                for row in type_result.fetchall()
            ]

            # Scope breakdown (ignore scope_filter for this one)
            scope_query = text("""
                SELECT c.scope_code, s.name, COUNT(*) as count
                FROM cases c
                JOIN scopes s ON c.scope_code = s.code
                GROUP BY c.scope_code, s.name
                ORDER BY count DESC
            """)
            scope_result = await db.execute(scope_query)
            total_all = sum(row[2] for row in scope_result.fetchall())

            # Re-execute to get data
            scope_result = await db.execute(scope_query)
            by_scope = [
                ScopeCount(
                    scope_code=row[0],
                    scope_name=row[1],
                    count=row[2],
                    percentage=round((row[2] / total_all * 100) if total_all > 0 else 0, 1),
                )
                for row in scope_result.fetchall()
            ]

            return CaseStatsResponse(
                by_status=by_status,
                by_severity=by_severity,
                by_type=by_type,
                by_scope=by_scope,
                total=total,
            )
        except Exception as e:
            logger.error(f"Failed to get case stats: {e}")
            raise

    async def get_case_trends(
        self,
        db: AsyncSession,
        days: int = 30,
        granularity: str = "day",
    ) -> TrendsResponse:
        """Get case creation and closure trends over time."""
        try:
            date_trunc = {
                "day": "day",
                "week": "week",
                "month": "month",
            }.get(granularity, "day")

            query = text(f"""
                WITH date_series AS (
                    SELECT generate_series(
                        DATE_TRUNC(:granularity, CURRENT_DATE - INTERVAL ':days days'),
                        DATE_TRUNC(:granularity, CURRENT_DATE),
                        INTERVAL '1 {date_trunc}'
                    )::date as date
                ),
                created_counts AS (
                    SELECT DATE_TRUNC(:granularity, created_at)::date as date, COUNT(*) as count
                    FROM cases
                    WHERE created_at >= CURRENT_DATE - INTERVAL ':days days'
                    GROUP BY DATE_TRUNC(:granularity, created_at)
                ),
                closed_counts AS (
                    SELECT DATE_TRUNC(:granularity, closed_at)::date as date, COUNT(*) as count
                    FROM cases
                    WHERE closed_at >= CURRENT_DATE - INTERVAL ':days days'
                    GROUP BY DATE_TRUNC(:granularity, closed_at)
                )
                SELECT
                    ds.date,
                    COALESCE(cc.count, 0) as created,
                    COALESCE(cl.count, 0) as closed
                FROM date_series ds
                LEFT JOIN created_counts cc ON ds.date = cc.date
                LEFT JOIN closed_counts cl ON ds.date = cl.date
                ORDER BY ds.date
            """.replace(":days", str(days)))

            result = await db.execute(query, {"granularity": date_trunc})
            rows = result.fetchall()

            data = [
                TrendDataPoint(date=row[0], created=row[1], closed=row[2])
                for row in rows
            ]

            total_created = sum(d.created for d in data)
            total_closed = sum(d.closed for d in data)

            return TrendsResponse(
                data=data,
                period_days=days,
                granularity=granularity,
                total_created=total_created,
                total_closed=total_closed,
            )
        except Exception as e:
            logger.error(f"Failed to get case trends: {e}")
            raise

    async def get_evidence_findings_stats(
        self, db: AsyncSession
    ) -> EvidenceFindingsStats:
        """Get evidence and findings statistics."""
        try:
            # Evidence by mime_type (simplified to type category)
            evidence_type_query = text("""
                SELECT
                    CASE
                        WHEN mime_type LIKE 'image/%' THEN 'Image'
                        WHEN mime_type LIKE 'application/pdf' THEN 'PDF'
                        WHEN mime_type LIKE 'text/%' THEN 'Text'
                        WHEN mime_type LIKE '%word%' OR mime_type LIKE '%document%' THEN 'Document'
                        WHEN mime_type LIKE '%spreadsheet%' OR mime_type LIKE '%excel%' THEN 'Spreadsheet'
                        WHEN mime_type LIKE 'video/%' THEN 'Video'
                        WHEN mime_type LIKE 'audio/%' THEN 'Audio'
                        ELSE 'Other'
                    END as type,
                    COUNT(*) as count
                FROM evidence
                GROUP BY
                    CASE
                        WHEN mime_type LIKE 'image/%' THEN 'Image'
                        WHEN mime_type LIKE 'application/pdf' THEN 'PDF'
                        WHEN mime_type LIKE 'text/%' THEN 'Text'
                        WHEN mime_type LIKE '%word%' OR mime_type LIKE '%document%' THEN 'Document'
                        WHEN mime_type LIKE '%spreadsheet%' OR mime_type LIKE '%excel%' THEN 'Spreadsheet'
                        WHEN mime_type LIKE 'video/%' THEN 'Video'
                        WHEN mime_type LIKE 'audio/%' THEN 'Audio'
                        ELSE 'Other'
                    END
                ORDER BY count DESC
            """)
            evidence_type_result = await db.execute(evidence_type_query)
            evidence_rows = evidence_type_result.fetchall()
            total_evidence = sum(row[1] for row in evidence_rows)
            evidence_by_type = [
                TypeCount(
                    type=row[0],
                    count=row[1],
                    percentage=round((row[1] / total_evidence * 100) if total_evidence > 0 else 0, 1),
                )
                for row in evidence_rows
            ]

            # Evidence doesn't have status column, so we'll skip evidence_by_status
            evidence_by_status: list[StatusCount] = []

            # Findings by severity
            findings_severity_query = text("""
                SELECT severity::text, COUNT(*) as count
                FROM findings
                GROUP BY severity
                ORDER BY
                    CASE severity
                        WHEN 'CRITICAL' THEN 1
                        WHEN 'HIGH' THEN 2
                        WHEN 'MEDIUM' THEN 3
                        WHEN 'LOW' THEN 4
                    END
            """)
            findings_severity_result = await db.execute(findings_severity_query)
            findings_rows = findings_severity_result.fetchall()
            total_findings = sum(row[1] for row in findings_rows)
            findings_by_severity = [
                SeverityCount(
                    severity=row[0],
                    count=row[1],
                    percentage=round((row[1] / total_findings * 100) if total_findings > 0 else 0, 1),
                )
                for row in findings_rows
            ]

            # Findings doesn't have status column either
            findings_by_status: list[StatusCount] = []

            return EvidenceFindingsStats(
                evidence_by_type=evidence_by_type,
                evidence_by_status=evidence_by_status,
                findings_by_severity=findings_by_severity,
                findings_by_status=findings_by_status,
                total_evidence=total_evidence,
                total_findings=total_findings,
            )
        except Exception as e:
            logger.error(f"Failed to get evidence/findings stats: {e}")
            raise

    async def get_entity_insights(
        self,
        db: AsyncSession,
        entity_type: Optional[str] = None,
        limit: int = 10,
    ) -> EntityInsightsResponse:
        """Get entity extraction insights."""
        try:
            # Entity type distribution
            type_query = text("""
                SELECT
                    entity_type,
                    COUNT(*) as count,
                    COUNT(DISTINCT value) as unique_values
                FROM case_entities
                GROUP BY entity_type
                ORDER BY count DESC
            """)
            type_result = await db.execute(type_query)
            by_type = [
                EntityTypeStats(
                    entity_type=row[0],
                    count=row[1],
                    unique_values=row[2],
                )
                for row in type_result.fetchall()
            ]

            # Top entities
            type_filter = "WHERE entity_type = :entity_type" if entity_type else ""
            params = {"entity_type": entity_type, "limit": limit} if entity_type else {"limit": limit}

            top_query = text(f"""
                SELECT
                    value,
                    entity_type,
                    SUM(occurrence_count) as occurrence_count,
                    COUNT(DISTINCT case_id) as case_count
                FROM case_entities
                {type_filter}
                GROUP BY value, entity_type
                ORDER BY occurrence_count DESC
                LIMIT :limit
            """)
            top_result = await db.execute(top_query, params)
            top_entities = [
                TopEntity(
                    value=row[0],
                    entity_type=row[1],
                    occurrence_count=row[2],
                    case_count=row[3],
                )
                for row in top_result.fetchall()
            ]

            # Total count
            total_query = text("SELECT COUNT(*) FROM case_entities")
            total_result = await db.execute(total_query)
            total_entities = total_result.scalar() or 0

            return EntityInsightsResponse(
                by_type=by_type,
                top_entities=top_entities,
                total_entities=total_entities,
            )
        except Exception as e:
            logger.error(f"Failed to get entity insights: {e}")
            raise

    async def get_user_activity(
        self,
        db: AsyncSession,
        days: int = 30,
        limit: int = 10,
    ) -> UserActivityResponse:
        """Get user activity metrics from audit log."""
        try:
            # Activity by action type
            action_query = text("""
                SELECT action, COUNT(*) as count
                FROM audit_log
                WHERE created_at >= CURRENT_DATE - INTERVAL ':days days'
                GROUP BY action
                ORDER BY count DESC
            """.replace(":days", str(days)))
            action_result = await db.execute(action_query)
            by_action = [
                ActionCount(action=row[0], count=row[1])
                for row in action_result.fetchall()
            ]

            # Top active users
            users_query = text("""
                SELECT
                    a.user_id::text,
                    u.email,
                    COUNT(*) as action_count,
                    MAX(a.created_at) as last_activity
                FROM audit_log a
                LEFT JOIN users u ON a.user_id = u.id
                WHERE a.created_at >= CURRENT_DATE - INTERVAL ':days days'
                  AND a.user_id IS NOT NULL
                GROUP BY a.user_id, u.email
                ORDER BY action_count DESC
                LIMIT :limit
            """.replace(":days", str(days)))
            users_result = await db.execute(users_query, {"limit": limit})
            top_users = [
                UserActivityStat(
                    user_id=row[0],
                    user_email=row[1] or "Unknown",
                    action_count=row[2],
                    last_activity=row[3],
                )
                for row in users_result.fetchall()
            ]

            # Total actions
            total_query = text("""
                SELECT COUNT(*) FROM audit_log
                WHERE created_at >= CURRENT_DATE - INTERVAL ':days days'
            """.replace(":days", str(days)))
            total_result = await db.execute(total_query)
            total_actions = total_result.scalar() or 0

            return UserActivityResponse(
                by_action=by_action,
                top_users=top_users,
                total_actions=total_actions,
                period_days=days,
            )
        except Exception as e:
            logger.error(f"Failed to get user activity: {e}")
            raise

    async def get_full_analytics(
        self,
        db: AsyncSession,
        days: int = 30,
    ) -> FullAnalyticsResponse:
        """Get complete analytics data for dashboard."""
        try:
            overview = await self.get_dashboard_overview(db)
            case_stats = await self.get_case_stats(db)
            trends = await self.get_case_trends(db, days=days)
            evidence_findings = await self.get_evidence_findings_stats(db)
            entities = await self.get_entity_insights(db)
            user_activity = await self.get_user_activity(db, days=days)

            return FullAnalyticsResponse(
                overview=overview,
                case_stats=case_stats,
                trends=trends,
                evidence_findings=evidence_findings,
                entities=entities,
                user_activity=user_activity,
            )
        except Exception as e:
            logger.error(f"Failed to get full analytics: {e}")
            raise


# Singleton instance
analytics_service = AnalyticsService()
