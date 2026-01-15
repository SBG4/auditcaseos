"""Entity schemas for AuditCaseOS API."""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import Field

from .common import BaseSchema, PaginatedResponse, TimestampMixin


class EntityType(str, Enum):
    """Types of entities that can be extracted."""

    EMPLOYEE_ID = "employee_id"
    IP_ADDRESS = "ip_address"
    EMAIL = "email"
    HOSTNAME = "hostname"
    MAC_ADDRESS = "mac_address"
    FILE_PATH = "file_path"
    USB_DEVICE = "usb_device"


class EntityBase(BaseSchema):
    """Base entity schema."""

    entity_type: EntityType = Field(
        ...,
        description="Type of entity",
        examples=[EntityType.IP_ADDRESS],
    )
    value: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Extracted entity value",
        examples=["192.168.1.100"],
    )


class EntityCreate(EntityBase):
    """Schema for manually creating an entity."""

    source: str | None = Field(
        default=None,
        max_length=255,
        description="Source of the entity",
        examples=["manual_entry"],
    )


class EntityResponse(EntityBase, TimestampMixin):
    """Schema for entity response."""

    id: UUID = Field(
        ...,
        description="Unique entity identifier",
    )
    case_id: UUID = Field(
        ...,
        description="Case this entity belongs to",
    )
    evidence_ids: list[UUID] | None = Field(
        default=None,
        description="Evidence items where entity was found",
    )
    source: str | None = Field(
        default=None,
        description="Where the entity was extracted from",
    )
    occurrence_count: int = Field(
        default=1,
        description="Number of times this entity was found",
    )

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "case_id": "550e8400-e29b-41d4-a716-446655440001",
                "entity_type": "ip_address",
                "value": "192.168.1.100",
                "evidence_ids": ["550e8400-e29b-41d4-a716-446655440002"],
                "source": "OCR extraction",
                "occurrence_count": 3,
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T14:45:00Z",
            }
        },
    }


class EntityListResponse(PaginatedResponse):
    """Paginated list of entities."""

    items: list[EntityResponse] = Field(
        ...,
        description="List of entities",
    )


class EntitySearchResponse(EntityResponse):
    """Entity with case information for search results."""

    case_id_str: str | None = Field(
        default=None,
        description="Human-readable case ID",
    )
    case_title: str | None = Field(
        default=None,
        description="Case title",
    )


class EntitySummary(BaseSchema):
    """Summary of entities by type."""

    entity_type: EntityType
    count: int


class EntityExtractionRequest(BaseSchema):
    """Request to extract entities from text."""

    text: str = Field(
        ...,
        min_length=1,
        max_length=100000,
        description="Text to extract entities from",
    )
    entity_types: list[EntityType] | None = Field(
        default=None,
        description="Specific entity types to extract (all if not specified)",
    )


class EntityExtractionResponse(BaseSchema):
    """Response from entity extraction."""

    extracted_count: int = Field(
        ...,
        description="Total number of entities extracted",
    )
    entities_by_type: dict[str, list[str]] = Field(
        ...,
        description="Extracted entities grouped by type",
    )


class EntityStoreRequest(BaseSchema):
    """Request to store extracted entities for a case."""

    case_id: str = Field(
        ...,
        description="Case ID (SCOPE-TYPE-SEQ format or UUID)",
    )
    evidence_id: UUID | None = Field(
        default=None,
        description="Evidence ID if entities are from evidence",
    )
    text: str = Field(
        ...,
        min_length=1,
        max_length=100000,
        description="Text to extract entities from",
    )
    source: str | None = Field(
        default="manual_extraction",
        max_length=255,
        description="Source description",
    )


class EntityStoreResponse(BaseSchema):
    """Response from storing extracted entities."""

    extracted_count: int = Field(
        ...,
        description="Total entities extracted from text",
    )
    stored_count: int = Field(
        ...,
        description="New entities stored (excludes duplicates)",
    )
    entities_by_type: dict[str, int] = Field(
        ...,
        description="Count of entities by type",
    )
