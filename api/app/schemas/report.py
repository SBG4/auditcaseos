"""Report schemas for AuditCaseOS API."""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import Field

from .common import BaseSchema, TimestampMixin
from .user import UserBrief


class ReportFormat(str, Enum):
    """Supported report output formats."""
    PDF = "PDF"
    DOCX = "DOCX"
    HTML = "HTML"
    MARKDOWN = "MARKDOWN"


class ReportTemplate(str, Enum):
    """Available report templates."""
    STANDARD = "STANDARD"
    EXECUTIVE_SUMMARY = "EXECUTIVE_SUMMARY"
    DETAILED = "DETAILED"
    COMPLIANCE = "COMPLIANCE"
    CUSTOM = "CUSTOM"


class ReportStatus(str, Enum):
    """Report generation status."""
    PENDING = "PENDING"
    GENERATING = "GENERATING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ReportSection(str, Enum):
    """Available report sections."""
    EXECUTIVE_SUMMARY = "EXECUTIVE_SUMMARY"
    CASE_DETAILS = "CASE_DETAILS"
    TIMELINE = "TIMELINE"
    FINDINGS = "FINDINGS"
    EVIDENCE = "EVIDENCE"
    RECOMMENDATIONS = "RECOMMENDATIONS"
    APPENDIX = "APPENDIX"


class ReportRequest(BaseSchema):
    """Schema for requesting report generation."""

    case_id: UUID = Field(
        ...,
        description="ID of the case to generate report for",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
    format: ReportFormat = Field(
        default=ReportFormat.PDF,
        description="Output format for the report",
        examples=[ReportFormat.PDF],
    )
    template: ReportTemplate = Field(
        default=ReportTemplate.STANDARD,
        description="Report template to use",
        examples=[ReportTemplate.STANDARD],
    )
    title: str | None = Field(
        default=None,
        max_length=255,
        description="Custom report title (defaults to case title)",
        examples=["Security Incident Report - USB Policy Violation"],
    )
    include_sections: list[ReportSection] | None = Field(
        default=None,
        description="Sections to include (defaults to all sections for template)",
        examples=[[ReportSection.EXECUTIVE_SUMMARY, ReportSection.FINDINGS, ReportSection.RECOMMENDATIONS]],
    )
    exclude_evidence_ids: list[UUID] | None = Field(
        default=None,
        description="Evidence IDs to exclude from the report",
    )
    exclude_finding_ids: list[UUID] | None = Field(
        default=None,
        description="Finding IDs to exclude from the report",
    )
    include_confidential: bool = Field(
        default=False,
        description="Include confidential/sensitive information",
    )
    watermark: str | None = Field(
        default=None,
        max_length=50,
        description="Watermark text to add to the report",
        examples=["CONFIDENTIAL", "DRAFT"],
    )
    custom_header: str | None = Field(
        default=None,
        max_length=500,
        description="Custom header text for the report",
    )
    custom_footer: str | None = Field(
        default=None,
        max_length=500,
        description="Custom footer text for the report",
    )
    recipients: list[str] | None = Field(
        default=None,
        description="Email addresses to send the report to upon completion",
        examples=[["manager@company.com", "compliance@company.com"]],
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "case_id": "550e8400-e29b-41d4-a716-446655440000",
                "format": "PDF",
                "template": "STANDARD",
                "title": "Security Incident Report - USB Policy Violation",
                "include_sections": ["EXECUTIVE_SUMMARY", "FINDINGS", "RECOMMENDATIONS"],
                "include_confidential": False,
                "watermark": "CONFIDENTIAL",
                "recipients": ["manager@company.com"],
            }
        },
    }


class ReportResponse(BaseSchema, TimestampMixin):
    """Schema for report response."""

    id: UUID = Field(
        ...,
        description="Unique report identifier",
        examples=["550e8400-e29b-41d4-a716-446655440004"],
    )
    case_id: UUID = Field(
        ...,
        description="ID of the case this report is for",
    )
    case_number: str = Field(
        ...,
        description="Case number (SCOPE-TYPE-SEQ format)",
        examples=["NYC-USB-00001"],
    )
    title: str = Field(
        ...,
        description="Report title",
        examples=["Security Incident Report - USB Policy Violation"],
    )
    format: ReportFormat = Field(
        ...,
        description="Report output format",
    )
    template: ReportTemplate = Field(
        ...,
        description="Report template used",
    )
    status: ReportStatus = Field(
        ...,
        description="Report generation status",
        examples=[ReportStatus.COMPLETED],
    )
    file_size: int | None = Field(
        default=None,
        ge=0,
        description="Report file size in bytes",
        examples=[1048576],
    )
    page_count: int | None = Field(
        default=None,
        ge=1,
        description="Number of pages in the report",
        examples=[15],
    )
    download_url: str | None = Field(
        default=None,
        description="URL to download the generated report",
        examples=["/api/v1/reports/550e8400-e29b-41d4-a716-446655440004/download"],
    )
    expires_at: datetime | None = Field(
        default=None,
        description="When the download URL expires",
    )
    error_message: str | None = Field(
        default=None,
        description="Error message if report generation failed",
    )
    generated_by: UserBrief = Field(
        ...,
        description="User who requested the report",
    )
    completed_at: datetime | None = Field(
        default=None,
        description="When the report generation completed",
    )

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440004",
                "case_id": "550e8400-e29b-41d4-a716-446655440000",
                "case_number": "NYC-USB-00001",
                "title": "Security Incident Report - USB Policy Violation",
                "format": "PDF",
                "template": "STANDARD",
                "status": "COMPLETED",
                "file_size": 1048576,
                "page_count": 15,
                "download_url": "/api/v1/reports/550e8400-e29b-41d4-a716-446655440004/download",
                "expires_at": "2024-01-16T10:30:00Z",
                "error_message": None,
                "generated_by": {
                    "id": "550e8400-e29b-41d4-a716-446655440001",
                    "full_name": "Jane Auditor",
                    "email": "jane.auditor@company.com",
                },
                "completed_at": "2024-01-15T10:35:00Z",
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:35:00Z",
            }
        },
    }


class ReportListResponse(BaseSchema):
    """List of reports."""

    items: list[ReportResponse] = Field(
        ...,
        description="List of reports",
    )
    total: int = Field(
        ...,
        description="Total number of reports",
    )
