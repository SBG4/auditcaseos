"""Evidence schemas for AuditCaseOS API."""

from datetime import datetime
from uuid import UUID

from pydantic import Field

from .common import BaseSchema, TimestampMixin
from .user import UserBrief


class EvidenceBase(BaseSchema):
    """Base evidence schema."""

    title: str = Field(
        ...,
        min_length=3,
        max_length=255,
        description="Evidence title",
        examples=["USB Device Log Export"],
    )
    description: str | None = Field(
        default=None,
        max_length=2000,
        description="Evidence description",
        examples=["Exported log showing USB device connection timestamps"],
    )
    evidence_type: str | None = Field(
        default=None,
        max_length=50,
        description="Type of evidence (e.g., log, screenshot, document)",
        examples=["log", "screenshot", "document", "email"],
    )


class EvidenceCreate(EvidenceBase):
    """Schema for creating evidence (metadata only, file uploaded separately)."""

    case_id: UUID = Field(
        ...,
        description="ID of the case this evidence belongs to",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
    source: str | None = Field(
        default=None,
        max_length=255,
        description="Source of the evidence",
        examples=["SIEM Export", "Manual Upload", "Email Archive"],
    )
    collected_at: datetime | None = Field(
        default=None,
        description="When the evidence was collected",
        examples=["2024-01-15T10:30:00Z"],
    )
    tags: list[str] | None = Field(
        default=None,
        description="Tags for categorizing the evidence",
        examples=[["usb-log", "primary"]],
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "case_id": "550e8400-e29b-41d4-a716-446655440000",
                "title": "USB Device Log Export",
                "description": "Exported log showing USB device connection timestamps",
                "evidence_type": "log",
                "source": "SIEM Export",
                "collected_at": "2024-01-15T10:30:00Z",
                "tags": ["usb-log", "primary"],
            }
        },
    }


class EvidenceUpdate(BaseSchema):
    """Schema for updating evidence metadata."""

    title: str | None = Field(
        default=None,
        min_length=3,
        max_length=255,
        description="Evidence title",
    )
    description: str | None = Field(
        default=None,
        max_length=2000,
        description="Evidence description",
    )
    evidence_type: str | None = Field(
        default=None,
        max_length=50,
        description="Type of evidence",
    )
    source: str | None = Field(
        default=None,
        max_length=255,
        description="Source of the evidence",
    )
    collected_at: datetime | None = Field(
        default=None,
        description="When the evidence was collected",
    )
    tags: list[str] | None = Field(
        default=None,
        description="Tags for categorizing the evidence",
    )


class FileInfo(BaseSchema):
    """File information for evidence."""

    filename: str = Field(
        ...,
        description="Original filename",
        examples=["usb_log_2024-01-15.csv"],
    )
    file_size: int = Field(
        ...,
        ge=0,
        description="File size in bytes",
        examples=[1024576],
    )
    mime_type: str = Field(
        ...,
        description="MIME type of the file",
        examples=["text/csv", "application/pdf", "image/png"],
    )
    checksum: str = Field(
        ...,
        description="SHA-256 checksum of the file",
        examples=["e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"],
    )
    storage_path: str = Field(
        ...,
        description="Internal storage path",
        examples=["evidence/2024/01/550e8400-e29b-41d4-a716-446655440000/usb_log.csv"],
    )


class EvidenceResponse(EvidenceBase, TimestampMixin):
    """Schema for evidence response."""

    id: UUID = Field(
        ...,
        description="Unique evidence identifier",
        examples=["550e8400-e29b-41d4-a716-446655440002"],
    )
    case_id: UUID = Field(
        ...,
        description="ID of the case this evidence belongs to",
    )
    source: str | None = Field(
        default=None,
        description="Source of the evidence",
    )
    collected_at: datetime | None = Field(
        default=None,
        description="When the evidence was collected",
    )
    tags: list[str] | None = Field(
        default=None,
        description="Tags for categorizing the evidence",
    )
    file_info: FileInfo | None = Field(
        default=None,
        description="File information if evidence has an attached file",
    )
    uploaded_by: UserBrief = Field(
        ...,
        description="User who uploaded the evidence",
    )
    download_url: str | None = Field(
        default=None,
        description="Presigned URL for downloading the evidence file",
        examples=["/api/v1/evidence/550e8400-e29b-41d4-a716-446655440002/download"],
    )

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440002",
                "case_id": "550e8400-e29b-41d4-a716-446655440000",
                "title": "USB Device Log Export",
                "description": "Exported log showing USB device connection timestamps",
                "evidence_type": "log",
                "source": "SIEM Export",
                "collected_at": "2024-01-15T10:30:00Z",
                "tags": ["usb-log", "primary"],
                "file_info": {
                    "filename": "usb_log_2024-01-15.csv",
                    "file_size": 1024576,
                    "mime_type": "text/csv",
                    "checksum": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                    "storage_path": "evidence/2024/01/550e8400.../usb_log.csv",
                },
                "uploaded_by": {
                    "id": "550e8400-e29b-41d4-a716-446655440001",
                    "full_name": "Jane Auditor",
                    "email": "jane.auditor@company.com",
                },
                "download_url": "/api/v1/evidence/550e8400-e29b-41d4-a716-446655440002/download",
                "created_at": "2024-01-15T11:00:00Z",
                "updated_at": "2024-01-15T11:00:00Z",
            }
        },
    }


class EvidenceListResponse(BaseSchema):
    """List of evidence items."""

    items: list[EvidenceResponse] = Field(
        ...,
        description="List of evidence items",
    )
    total: int = Field(
        ...,
        description="Total number of evidence items",
    )
