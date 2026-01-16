"""Evidence model for AuditCaseOS."""

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .case import Case
    from .user import User


class EvidenceType(str, enum.Enum):
    """Enumeration of evidence types."""
    DOCUMENT = "DOCUMENT"
    IMAGE = "IMAGE"
    VIDEO = "VIDEO"
    AUDIO = "AUDIO"
    LOG_FILE = "LOG_FILE"
    EMAIL = "EMAIL"
    SCREENSHOT = "SCREENSHOT"
    DATABASE_EXPORT = "DATABASE_EXPORT"
    OTHER = "OTHER"


class EvidenceStatus(str, enum.Enum):
    """Enumeration of evidence statuses."""
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    ARCHIVED = "ARCHIVED"


class Evidence(Base):
    """Evidence model representing case evidence files and data.

    Attributes:
        id: UUID primary key (inherited from Base)
        case_id: UUID reference to the associated case
        evidence_type: Type of evidence
        status: Current status of the evidence
        filename: Original filename of the evidence
        file_path: Storage path of the evidence file
        file_size: Size of the file in bytes
        mime_type: MIME type of the file
        checksum: SHA-256 hash of the file for integrity verification
        description: Description of the evidence
        uploaded_by: UUID of the user who uploaded the evidence
        uploaded_at: Timestamp when evidence was uploaded
        verified_by: UUID of the user who verified the evidence
        verified_at: Timestamp when evidence was verified
        metadata: JSONB field for additional structured data
        created_at: Timestamp when record was created (inherited)
        updated_at: Timestamp when record was last updated (inherited)
    """

    __tablename__ = "evidence"

    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    evidence_type: Mapped[EvidenceType] = mapped_column(
        Enum(EvidenceType, name="evidence_type_enum", create_type=True),
        nullable=False,
        index=True,
    )

    status: Mapped[EvidenceStatus] = mapped_column(
        Enum(EvidenceStatus, name="evidence_status_enum", create_type=True),
        default=EvidenceStatus.PENDING,
        nullable=False,
        index=True,
    )

    filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    file_path: Mapped[str] = mapped_column(
        String(1024),
        nullable=False,
    )

    file_size: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )

    mime_type: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    checksum: Mapped[str | None] = mapped_column(
        String(64),  # SHA-256 produces 64 hex characters
        nullable=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    verified_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    metadata: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    # Relationships
    case: Mapped["Case"] = relationship(
        "Case",
        back_populates="evidence",
        lazy="selectin",
    )

    uploader: Mapped["User"] = relationship(
        "User",
        back_populates="uploaded_evidence",
        foreign_keys=[uploaded_by],
        lazy="selectin",
    )

    verifier: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[verified_by],
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Evidence(id={self.id}, filename='{self.filename}', type={self.evidence_type.value})>"
