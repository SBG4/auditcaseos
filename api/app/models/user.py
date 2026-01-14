"""User model for AuditCaseOS."""

from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .case import Case
    from .audit_log import AuditLog
    from .evidence import Evidence


class User(Base):
    """User model representing system users.

    Attributes:
        id: UUID primary key (inherited from Base)
        username: Unique username for login
        email: Unique email address
        full_name: User's full display name
        department: Department the user belongs to
        is_active: Whether the user account is active
        created_at: Timestamp when user was created (inherited)
        updated_at: Timestamp when user was last updated (inherited)
    """

    __tablename__ = "users"

    username: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )

    full_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    department: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # Relationships
    owned_cases: Mapped[list["Case"]] = relationship(
        "Case",
        back_populates="owner",
        foreign_keys="Case.owner_id",
        lazy="selectin",
    )

    assigned_cases: Mapped[list["Case"]] = relationship(
        "Case",
        back_populates="assignee",
        foreign_keys="Case.assigned_to",
        lazy="selectin",
    )

    audit_logs: Mapped[list["AuditLog"]] = relationship(
        "AuditLog",
        back_populates="user",
        lazy="selectin",
    )

    uploaded_evidence: Mapped[list["Evidence"]] = relationship(
        "Evidence",
        back_populates="uploader",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"
