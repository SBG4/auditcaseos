"""Case model for AuditCaseOS."""

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .evidence import Evidence
    from .finding import Finding
    from .scope import Scope
    from .user import User


class CaseType(str, enum.Enum):
    """Enumeration of case types."""
    USB = "USB"
    EMAIL = "EMAIL"
    WEB = "WEB"
    POLICY = "POLICY"


class CaseStatus(str, enum.Enum):
    """Enumeration of case statuses."""
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    PENDING_REVIEW = "PENDING_REVIEW"
    CLOSED = "CLOSED"
    ARCHIVED = "ARCHIVED"


class CaseSeverity(str, enum.Enum):
    """Enumeration of case severity levels."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Case(Base):
    """Case model representing audit cases.

    Attributes:
        id: UUID primary key (inherited from Base)
        case_id: Human-readable case identifier (SCOPE-TYPE-SEQ format)
        scope_code: Reference to the scope code
        case_type: Type of case (USB, EMAIL, WEB, POLICY)
        status: Current status of the case
        severity: Severity level of the case
        title: Brief title of the case
        summary: Short summary of the case
        description: Detailed description of the case
        subject_user: User who is the subject of the case
        subject_computer: Computer involved in the case
        subject_devices: Array of devices involved
        related_users: Array of related user identifiers
        owner_id: UUID of the case owner
        assigned_to: UUID of the assigned investigator
        incident_date: Date when the incident occurred
        closed_at: Timestamp when the case was closed
        tags: Array of tags for categorization
        metadata: JSONB field for additional structured data
        created_at: Timestamp when case was created (inherited)
        updated_at: Timestamp when case was last updated (inherited)
    """

    __tablename__ = "cases"

    case_id: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )

    scope_code: Mapped[str] = mapped_column(
        String(10),
        ForeignKey("scopes.code", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    case_type: Mapped[CaseType] = mapped_column(
        Enum(CaseType, name="case_type_enum", create_type=True),
        nullable=False,
        index=True,
    )

    status: Mapped[CaseStatus] = mapped_column(
        Enum(CaseStatus, name="case_status_enum", create_type=True),
        default=CaseStatus.OPEN,
        nullable=False,
        index=True,
    )

    severity: Mapped[CaseSeverity] = mapped_column(
        Enum(CaseSeverity, name="case_severity_enum", create_type=True),
        default=CaseSeverity.MEDIUM,
        nullable=False,
        index=True,
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    summary: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    subject_user: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    subject_computer: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )

    subject_devices: Mapped[Optional[list[str]]] = mapped_column(
        ARRAY(String(255)),
        nullable=True,
    )

    related_users: Mapped[Optional[list[str]]] = mapped_column(
        ARRAY(String(255)),
        nullable=True,
    )

    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    assigned_to: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    incident_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    closed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    tags: Mapped[Optional[list[str]]] = mapped_column(
        ARRAY(String(50)),
        nullable=True,
    )

    metadata: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
    )

    # Relationships
    scope: Mapped["Scope"] = relationship(
        "Scope",
        back_populates="cases",
        lazy="selectin",
    )

    owner: Mapped["User"] = relationship(
        "User",
        back_populates="owned_cases",
        foreign_keys=[owner_id],
        lazy="selectin",
    )

    assignee: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="assigned_cases",
        foreign_keys=[assigned_to],
        lazy="selectin",
    )

    evidence: Mapped[list["Evidence"]] = relationship(
        "Evidence",
        back_populates="case",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    findings: Mapped[list["Finding"]] = relationship(
        "Finding",
        back_populates="case",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Case(id={self.id}, case_id='{self.case_id}', status={self.status.value})>"
