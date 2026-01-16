"""Case schemas for AuditCaseOS API."""

from datetime import date
from uuid import UUID

from pydantic import Field

from .common import (
    BaseSchema,
    CaseStatus,
    CaseType,
    PaginatedResponse,
    Severity,
    TimestampMixin,
)
from .user import UserBrief


class CaseBase(BaseSchema):
    """Base case schema with common fields."""

    scope_code: str = Field(
        ...,
        min_length=2,
        max_length=10,
        pattern=r"^[A-Z0-9]+$",
        description="Scope code (e.g., HQ, NYC, LON)",
        examples=["HQ", "NYC", "LON"],
    )
    case_type: CaseType = Field(
        ...,
        description="Type of audit case",
        examples=[CaseType.USB],
    )
    title: str = Field(
        ...,
        min_length=5,
        max_length=255,
        description="Case title",
        examples=["Unauthorized USB device usage detected"],
    )
    summary: str = Field(
        ...,
        min_length=10,
        max_length=1000,
        description="Brief case summary",
        examples=["Employee connected unauthorized USB storage device to workstation."],
    )
    description: str | None = Field(
        default=None,
        max_length=10000,
        description="Detailed case description",
        examples=["On 2024-01-15, security monitoring detected an unauthorized USB..."],
    )
    severity: Severity = Field(
        default=Severity.MEDIUM,
        description="Case severity level",
        examples=[Severity.HIGH],
    )


class CaseCreate(CaseBase):
    """Schema for creating a new case."""

    subject_user: str | None = Field(
        default=None,
        max_length=255,
        description="Primary subject user of the case",
        examples=["jsmith"],
    )
    subject_computer: str | None = Field(
        default=None,
        max_length=255,
        description="Subject computer/workstation name",
        examples=["WS-NYC-1234"],
    )
    subject_devices: list[str] | None = Field(
        default=None,
        description="List of subject device identifiers",
        examples=[["USB-001", "USB-002"]],
    )
    related_users: list[str] | None = Field(
        default=None,
        description="List of related user identifiers",
        examples=[["jdoe", "asmith"]],
    )
    incident_date: date | None = Field(
        default=None,
        description="Date when the incident occurred",
        examples=["2024-01-15"],
    )
    tags: list[str] | None = Field(
        default=None,
        max_length=50,
        description="Tags for categorizing the case",
        examples=[["data-breach", "usb", "priority"]],
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "scope_code": "NYC",
                "case_type": "USB",
                "title": "Unauthorized USB device usage detected",
                "summary": "Employee connected unauthorized USB storage device to workstation.",
                "description": "On 2024-01-15, security monitoring detected an unauthorized USB device...",
                "severity": "HIGH",
                "subject_user": "jsmith",
                "subject_computer": "WS-NYC-1234",
                "subject_devices": ["USB-001"],
                "related_users": ["jdoe"],
                "incident_date": "2024-01-15",
                "tags": ["data-breach", "usb"],
            }
        },
    }


class CaseUpdate(BaseSchema):
    """Schema for updating a case. All fields are optional."""

    title: str | None = Field(
        default=None,
        min_length=5,
        max_length=255,
        description="Case title",
    )
    summary: str | None = Field(
        default=None,
        min_length=10,
        max_length=1000,
        description="Brief case summary",
    )
    description: str | None = Field(
        default=None,
        max_length=10000,
        description="Detailed case description",
    )
    severity: Severity | None = Field(
        default=None,
        description="Case severity level",
    )
    status: CaseStatus | None = Field(
        default=None,
        description="Case status",
    )
    subject_user: str | None = Field(
        default=None,
        max_length=255,
        description="Primary subject user of the case",
    )
    subject_computer: str | None = Field(
        default=None,
        max_length=255,
        description="Subject computer/workstation name",
    )
    subject_devices: list[str] | None = Field(
        default=None,
        description="List of subject device identifiers",
    )
    related_users: list[str] | None = Field(
        default=None,
        description="List of related user identifiers",
    )
    incident_date: date | None = Field(
        default=None,
        description="Date when the incident occurred",
    )
    tags: list[str] | None = Field(
        default=None,
        description="Tags for categorizing the case",
    )
    assigned_to_id: UUID | None = Field(
        default=None,
        description="ID of user to assign the case to",
    )


class CaseResponse(CaseBase, TimestampMixin):
    """Schema for case response."""

    id: UUID = Field(
        ...,
        description="Unique case identifier (internal)",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
    case_id: str = Field(
        ...,
        description="Generated case ID (SCOPE-TYPE-SEQ format)",
        examples=["NYC-USB-00001"],
    )
    status: CaseStatus = Field(
        ...,
        description="Current case status",
        examples=[CaseStatus.OPEN],
    )
    subject_user: str | None = Field(
        default=None,
        description="Primary subject user of the case",
    )
    subject_computer: str | None = Field(
        default=None,
        description="Subject computer/workstation name",
    )
    subject_devices: list[str] | None = Field(
        default=None,
        description="List of subject device identifiers",
    )
    related_users: list[str] | None = Field(
        default=None,
        description="List of related user identifiers",
    )
    incident_date: date | None = Field(
        default=None,
        description="Date when the incident occurred",
    )
    tags: list[str] | None = Field(
        default=None,
        description="Tags for categorizing the case",
    )
    owner: UserBrief = Field(
        ...,
        description="Case owner information",
    )
    assigned_to: UserBrief | None = Field(
        default=None,
        description="User assigned to the case",
    )
    evidence_count: int = Field(
        default=0,
        description="Number of evidence items attached",
    )
    findings_count: int = Field(
        default=0,
        description="Number of findings recorded",
    )

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "case_id": "NYC-USB-00001",
                "scope_code": "NYC",
                "case_type": "USB",
                "title": "Unauthorized USB device usage detected",
                "summary": "Employee connected unauthorized USB storage device to workstation.",
                "description": "On 2024-01-15, security monitoring detected...",
                "severity": "HIGH",
                "status": "OPEN",
                "subject_user": "jsmith",
                "subject_computer": "WS-NYC-1234",
                "subject_devices": ["USB-001"],
                "related_users": ["jdoe"],
                "incident_date": "2024-01-15",
                "tags": ["data-breach", "usb"],
                "owner": {
                    "id": "550e8400-e29b-41d4-a716-446655440001",
                    "full_name": "Jane Auditor",
                    "email": "jane.auditor@company.com",
                },
                "assigned_to": None,
                "evidence_count": 3,
                "findings_count": 2,
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T14:45:00Z",
            }
        },
    }


class CaseListResponse(PaginatedResponse):
    """Paginated list of cases."""

    items: list[CaseResponse] = Field(
        ...,
        description="List of cases",
    )


class CaseFilter(BaseSchema):
    """Schema for filtering cases."""

    status: CaseStatus | None = Field(
        default=None,
        description="Filter by case status",
    )
    case_type: CaseType | None = Field(
        default=None,
        description="Filter by case type",
    )
    scope_code: str | None = Field(
        default=None,
        description="Filter by scope code",
    )
    severity: Severity | None = Field(
        default=None,
        description="Filter by severity level",
    )
    owner_id: UUID | None = Field(
        default=None,
        description="Filter by case owner",
    )
    assigned_to_id: UUID | None = Field(
        default=None,
        description="Filter by assigned user",
    )
    date_from: date | None = Field(
        default=None,
        description="Filter cases created on or after this date",
    )
    date_to: date | None = Field(
        default=None,
        description="Filter cases created on or before this date",
    )
    incident_date_from: date | None = Field(
        default=None,
        description="Filter by incident date (from)",
    )
    incident_date_to: date | None = Field(
        default=None,
        description="Filter by incident date (to)",
    )
    search: str | None = Field(
        default=None,
        min_length=2,
        max_length=100,
        description="Search in title, summary, and case_id",
    )
    tags: list[str] | None = Field(
        default=None,
        description="Filter by tags (any match)",
    )
