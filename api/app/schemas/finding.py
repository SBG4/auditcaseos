"""Finding schemas for AuditCaseOS API."""

from datetime import datetime
from uuid import UUID

from pydantic import Field

from .common import BaseSchema, Severity, TimestampMixin
from .user import UserBrief


class FindingStatus(str):
    """Status of a finding."""
    DRAFT = "DRAFT"
    CONFIRMED = "CONFIRMED"
    DISPUTED = "DISPUTED"
    RESOLVED = "RESOLVED"


class FindingBase(BaseSchema):
    """Base finding schema."""

    title: str = Field(
        ...,
        min_length=5,
        max_length=255,
        description="Finding title",
        examples=["Unauthorized data transfer to USB device"],
    )
    description: str = Field(
        ...,
        min_length=10,
        max_length=10000,
        description="Detailed finding description",
        examples=["Analysis of logs revealed unauthorized transfer of 2.5GB data..."],
    )
    severity: Severity = Field(
        ...,
        description="Finding severity level",
        examples=[Severity.HIGH],
    )
    finding_type: str | None = Field(
        default=None,
        max_length=100,
        description="Type/category of finding",
        examples=["policy-violation", "data-exfiltration", "unauthorized-access"],
    )


class FindingCreate(FindingBase):
    """Schema for creating a new finding."""

    case_id: UUID = Field(
        ...,
        description="ID of the case this finding belongs to",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
    evidence_ids: list[UUID] | None = Field(
        default=None,
        description="List of evidence IDs supporting this finding",
        examples=[["550e8400-e29b-41d4-a716-446655440002"]],
    )
    recommendation: str | None = Field(
        default=None,
        max_length=5000,
        description="Recommended actions or remediation steps",
        examples=["Revoke USB access privileges and conduct security awareness training"],
    )
    impact: str | None = Field(
        default=None,
        max_length=2000,
        description="Impact assessment of the finding",
        examples=["Potential exposure of confidential customer data"],
    )
    root_cause: str | None = Field(
        default=None,
        max_length=2000,
        description="Root cause analysis",
        examples=["Inadequate USB device control policies"],
    )
    tags: list[str] | None = Field(
        default=None,
        description="Tags for categorizing the finding",
        examples=[["data-leak", "usb", "critical"]],
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "case_id": "550e8400-e29b-41d4-a716-446655440000",
                "title": "Unauthorized data transfer to USB device",
                "description": "Analysis of logs revealed unauthorized transfer of 2.5GB data...",
                "severity": "HIGH",
                "finding_type": "data-exfiltration",
                "evidence_ids": ["550e8400-e29b-41d4-a716-446655440002"],
                "recommendation": "Revoke USB access privileges and conduct security awareness training",
                "impact": "Potential exposure of confidential customer data",
                "root_cause": "Inadequate USB device control policies",
                "tags": ["data-leak", "usb"],
            }
        },
    }


class FindingUpdate(BaseSchema):
    """Schema for updating a finding. All fields are optional."""

    title: str | None = Field(
        default=None,
        min_length=5,
        max_length=255,
        description="Finding title",
    )
    description: str | None = Field(
        default=None,
        min_length=10,
        max_length=10000,
        description="Detailed finding description",
    )
    severity: Severity | None = Field(
        default=None,
        description="Finding severity level",
    )
    finding_type: str | None = Field(
        default=None,
        max_length=100,
        description="Type/category of finding",
    )
    status: str | None = Field(
        default=None,
        description="Finding status (DRAFT, CONFIRMED, DISPUTED, RESOLVED)",
    )
    evidence_ids: list[UUID] | None = Field(
        default=None,
        description="List of evidence IDs supporting this finding",
    )
    recommendation: str | None = Field(
        default=None,
        max_length=5000,
        description="Recommended actions or remediation steps",
    )
    impact: str | None = Field(
        default=None,
        max_length=2000,
        description="Impact assessment of the finding",
    )
    root_cause: str | None = Field(
        default=None,
        max_length=2000,
        description="Root cause analysis",
    )
    tags: list[str] | None = Field(
        default=None,
        description="Tags for categorizing the finding",
    )
    resolution_notes: str | None = Field(
        default=None,
        max_length=5000,
        description="Notes about how the finding was resolved",
    )


class FindingResponse(FindingBase, TimestampMixin):
    """Schema for finding response."""

    id: UUID = Field(
        ...,
        description="Unique finding identifier",
        examples=["550e8400-e29b-41d4-a716-446655440003"],
    )
    case_id: UUID = Field(
        ...,
        description="ID of the case this finding belongs to",
    )
    finding_number: int = Field(
        ...,
        ge=1,
        description="Sequential finding number within the case",
        examples=[1],
    )
    status: str = Field(
        default="DRAFT",
        description="Finding status",
        examples=["CONFIRMED"],
    )
    evidence_ids: list[UUID] | None = Field(
        default=None,
        description="List of evidence IDs supporting this finding",
    )
    recommendation: str | None = Field(
        default=None,
        description="Recommended actions or remediation steps",
    )
    impact: str | None = Field(
        default=None,
        description="Impact assessment of the finding",
    )
    root_cause: str | None = Field(
        default=None,
        description="Root cause analysis",
    )
    tags: list[str] | None = Field(
        default=None,
        description="Tags for categorizing the finding",
    )
    resolution_notes: str | None = Field(
        default=None,
        description="Notes about how the finding was resolved",
    )
    resolved_at: datetime | None = Field(
        default=None,
        description="When the finding was resolved",
    )
    created_by: UserBrief = Field(
        ...,
        description="User who created the finding",
    )

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440003",
                "case_id": "550e8400-e29b-41d4-a716-446655440000",
                "finding_number": 1,
                "title": "Unauthorized data transfer to USB device",
                "description": "Analysis of logs revealed unauthorized transfer of 2.5GB data...",
                "severity": "HIGH",
                "finding_type": "data-exfiltration",
                "status": "CONFIRMED",
                "evidence_ids": ["550e8400-e29b-41d4-a716-446655440002"],
                "recommendation": "Revoke USB access privileges and conduct security awareness training",
                "impact": "Potential exposure of confidential customer data",
                "root_cause": "Inadequate USB device control policies",
                "tags": ["data-leak", "usb"],
                "resolution_notes": None,
                "resolved_at": None,
                "created_by": {
                    "id": "550e8400-e29b-41d4-a716-446655440001",
                    "full_name": "Jane Auditor",
                    "email": "jane.auditor@company.com",
                },
                "created_at": "2024-01-15T12:00:00Z",
                "updated_at": "2024-01-15T14:30:00Z",
            }
        },
    }


class FindingListResponse(BaseSchema):
    """List of findings."""

    items: list[FindingResponse] = Field(
        ...,
        description="List of findings",
    )
    total: int = Field(
        ...,
        description="Total number of findings",
    )
