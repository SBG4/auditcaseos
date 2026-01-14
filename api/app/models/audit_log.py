"""AuditLog model for AuditCaseOS."""

import enum
import uuid
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .user import User


class AuditAction(str, enum.Enum):
    """Enumeration of audit log actions."""
    # Case actions
    CASE_CREATE = "CASE_CREATE"
    CASE_UPDATE = "CASE_UPDATE"
    CASE_DELETE = "CASE_DELETE"
    CASE_VIEW = "CASE_VIEW"
    CASE_ASSIGN = "CASE_ASSIGN"
    CASE_STATUS_CHANGE = "CASE_STATUS_CHANGE"
    CASE_CLOSE = "CASE_CLOSE"
    CASE_REOPEN = "CASE_REOPEN"

    # Evidence actions
    EVIDENCE_UPLOAD = "EVIDENCE_UPLOAD"
    EVIDENCE_DELETE = "EVIDENCE_DELETE"
    EVIDENCE_VIEW = "EVIDENCE_VIEW"
    EVIDENCE_DOWNLOAD = "EVIDENCE_DOWNLOAD"
    EVIDENCE_VERIFY = "EVIDENCE_VERIFY"

    # Finding actions
    FINDING_CREATE = "FINDING_CREATE"
    FINDING_UPDATE = "FINDING_UPDATE"
    FINDING_DELETE = "FINDING_DELETE"
    FINDING_REVIEW = "FINDING_REVIEW"

    # User actions
    USER_LOGIN = "USER_LOGIN"
    USER_LOGOUT = "USER_LOGOUT"
    USER_CREATE = "USER_CREATE"
    USER_UPDATE = "USER_UPDATE"
    USER_DEACTIVATE = "USER_DEACTIVATE"

    # System actions
    SYSTEM_CONFIG_CHANGE = "SYSTEM_CONFIG_CHANGE"
    EXPORT = "EXPORT"
    IMPORT = "IMPORT"


class AuditLog(Base):
    """AuditLog model for tracking all system actions.

    This model provides a complete audit trail of all actions performed
    in the system for security and compliance purposes.

    Attributes:
        id: UUID primary key (inherited from Base)
        user_id: UUID of the user who performed the action
        action: Type of action performed
        resource_type: Type of resource affected (e.g., 'case', 'evidence')
        resource_id: UUID of the affected resource
        description: Human-readable description of the action
        old_values: Previous values before the change (for updates)
        new_values: New values after the change (for updates)
        ip_address: IP address from which the action was performed
        user_agent: User agent string of the client
        metadata: JSONB field for additional context
        created_at: Timestamp when action was performed (inherited)
        updated_at: Timestamp when record was last updated (inherited)
    """

    __tablename__ = "audit_logs"

    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    action: Mapped[AuditAction] = mapped_column(
        Enum(AuditAction, name="audit_action_enum", create_type=True),
        nullable=False,
        index=True,
    )

    resource_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    resource_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
    )

    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    old_values: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
    )

    new_values: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
    )

    ip_address: Mapped[Optional[str]] = mapped_column(
        String(45),  # IPv6 max length
        nullable=True,
    )

    user_agent: Mapped[Optional[str]] = mapped_column(
        String(512),
        nullable=True,
    )

    metadata: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
    )

    # Relationships
    user: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="audit_logs",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<AuditLog(id={self.id}, action={self.action.value}, resource_type='{self.resource_type}')>"
