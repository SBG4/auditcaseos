"""Analytics schemas for dashboard statistics and trends."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class StatusCount(BaseModel):
    """Count of cases by status."""
    status: str
    count: int
    percentage: float


class SeverityCount(BaseModel):
    """Count of cases/findings by severity."""
    severity: str
    count: int
    percentage: float


class TypeCount(BaseModel):
    """Count by type (case type, evidence type, etc.)."""
    type: str
    count: int
    percentage: float


class ScopeCount(BaseModel):
    """Count of cases by scope."""
    scope_code: str
    scope_name: str
    count: int
    percentage: float


class TrendDataPoint(BaseModel):
    """Single data point for time series trends."""
    date: date
    created: int
    closed: int


class EntityTypeStats(BaseModel):
    """Statistics for entity types."""
    entity_type: str
    count: int
    unique_values: int


class TopEntity(BaseModel):
    """Top occurring entity value."""
    value: str
    entity_type: str
    occurrence_count: int
    case_count: int


class UserActivityStat(BaseModel):
    """User activity statistics."""
    user_id: str
    user_email: str
    action_count: int
    last_activity: datetime


class ActionCount(BaseModel):
    """Count of actions by type."""
    action: str
    count: int


# Response Models

class DashboardOverview(BaseModel):
    """Overview statistics for dashboard cards."""
    total_cases: int
    open_cases: int
    in_progress_cases: int
    closed_cases: int
    critical_cases: int
    high_severity_cases: int
    total_evidence: int
    total_findings: int
    total_entities: int
    avg_resolution_days: float | None = None


class CaseStatsResponse(BaseModel):
    """Complete case statistics breakdown."""
    by_status: list[StatusCount]
    by_severity: list[SeverityCount]
    by_type: list[TypeCount]
    by_scope: list[ScopeCount]
    total: int


class TrendsResponse(BaseModel):
    """Case trends over time."""
    data: list[TrendDataPoint]
    period_days: int
    granularity: str
    total_created: int
    total_closed: int


class EvidenceFindingsStats(BaseModel):
    """Evidence and findings statistics."""
    evidence_by_type: list[TypeCount]
    evidence_by_status: list[StatusCount]
    findings_by_severity: list[SeverityCount]
    findings_by_status: list[StatusCount]
    total_evidence: int
    total_findings: int


class EntityInsightsResponse(BaseModel):
    """Entity extraction insights."""
    by_type: list[EntityTypeStats]
    top_entities: list[TopEntity]
    total_entities: int


class UserActivityResponse(BaseModel):
    """User activity metrics."""
    by_action: list[ActionCount]
    top_users: list[UserActivityStat]
    total_actions: int
    period_days: int


class FullAnalyticsResponse(BaseModel):
    """Complete analytics data for dashboard."""
    model_config = ConfigDict(from_attributes=True)

    overview: DashboardOverview
    case_stats: CaseStatsResponse
    trends: TrendsResponse
    evidence_findings: EvidenceFindingsStats
    entities: EntityInsightsResponse
    user_activity: UserActivityResponse
