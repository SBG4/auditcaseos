"""Scope model for AuditCaseOS."""

from typing import TYPE_CHECKING, Optional

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .case import Case


class Scope(Base):
    """Scope model representing audit scope categories.

    Scopes define the organizational area or department that a case belongs to.
    Examples: FIN (Finance), HR (Human Resources), IT (Information Technology)

    Attributes:
        id: UUID primary key (inherited from Base)
        code: Unique short code for the scope (e.g., FIN, HR, IT)
        name: Full name of the scope
        description: Detailed description of the scope
        created_at: Timestamp when scope was created (inherited)
        updated_at: Timestamp when scope was last updated (inherited)
    """

    __tablename__ = "scopes"

    code: Mapped[str] = mapped_column(
        String(10),
        unique=True,
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    cases: Mapped[list["Case"]] = relationship(
        "Case",
        back_populates="scope",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Scope(id={self.id}, code='{self.code}', name='{self.name}')>"
