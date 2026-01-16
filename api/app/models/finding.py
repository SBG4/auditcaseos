"""Finding model for AuditCaseOS."""

import enum
import uuid
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .case import Case
    from .user import User


class FindingSeverity(str, enum.Enum):
    """Enumeration of finding severity levels."""
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class FindingStatus(str, enum.Enum):
    """Enumeration of finding statuses."""
    DRAFT = "DRAFT"
    CONFIRMED = "CONFIRMED"
    DISPUTED = "DISPUTED"
    RESOLVED = "RESOLVED"


class Finding(Base):
    """Finding model representing case findings and conclusions.

    Attributes:
        id: UUID primary key (inherited from Base)
        case_id: UUID reference to the associated case
        title: Brief title of the finding
        description: Detailed description of the finding
        severity: Severity level of the finding
        status: Current status of the finding
        evidence_ids: Array of evidence UUIDs that support this finding
        recommendation: Recommended action or remediation
        created_by: UUID of the user who created the finding
        reviewed_by: UUID of the user who reviewed the finding
        metadata: JSONB field for additional structured data
        created_at: Timestamp when finding was created (inherited)
        updated_at: Timestamp when finding was last updated (inherited)
    """

    __tablename__ = "findings"

    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    severity: Mapped[FindingSeverity] = mapped_column(
        Enum(FindingSeverity, name="finding_severity_enum", create_type=True),
        default=FindingSeverity.MEDIUM,
        nullable=False,
        index=True,
    )

    status: Mapped[FindingStatus] = mapped_column(
        Enum(FindingStatus, name="finding_status_enum", create_type=True),
        default=FindingStatus.DRAFT,
        nullable=False,
        index=True,
    )

    evidence_ids: Mapped[list[uuid.UUID] | None] = mapped_column(
        ARRAY(UUID(as_uuid=True)),
        nullable=True,
    )

    recommendation: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Note: 'metadata' is reserved in SQLAlchemy 2.x, use 'extra_data' as attribute name
    extra_data: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata",  # Keep the column name as 'metadata' in the database
        JSONB,
        nullable=True,
    )

    # Relationships
    case: Mapped["Case"] = relationship(
        "Case",
        back_populates="findings",
        lazy="selectin",
    )

    creator: Mapped["User"] = relationship(
        "User",
        foreign_keys=[created_by],
        lazy="selectin",
    )

    reviewer: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[reviewed_by],
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Finding(id={self.id}, title='{self.title}', severity={self.severity.value})>"
