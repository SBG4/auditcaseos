"""Common schemas and enums for AuditCaseOS API."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict


class CaseType(str, Enum):
    """Type of audit case."""
    USB = "USB"
    EMAIL = "EMAIL"
    WEB = "WEB"
    POLICY = "POLICY"


class CaseStatus(str, Enum):
    """Status of an audit case."""
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    PENDING_REVIEW = "PENDING_REVIEW"
    CLOSED = "CLOSED"
    ARCHIVED = "ARCHIVED"


class Severity(str, Enum):
    """Severity level of a case or finding."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class BaseSchema(BaseModel):
    """Base schema with common configuration."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        str_strip_whitespace=True,
        validate_assignment=True,
    )


class TimestampMixin(BaseModel):
    """Mixin for timestamp fields."""

    created_at: datetime
    updated_at: datetime


class PaginationParams(BaseSchema):
    """Pagination parameters for list endpoints."""

    page: int = 1
    page_size: int = 20

    @property
    def offset(self) -> int:
        """Calculate offset for database query."""
        return (self.page - 1) * self.page_size


class PaginatedResponse(BaseSchema):
    """Base schema for paginated responses."""

    total: int
    page: int
    page_size: int
    total_pages: int

    @classmethod
    def calculate_total_pages(cls, total: int, page_size: int) -> int:
        """Calculate total pages from total items and page size."""
        return (total + page_size - 1) // page_size if page_size > 0 else 0


class MessageResponse(BaseSchema):
    """Simple message response."""

    message: str
    details: dict[str, Any] | None = None
