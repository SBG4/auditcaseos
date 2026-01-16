"""User schemas for AuditCaseOS API."""

from uuid import UUID

from pydantic import EmailStr, Field

from .common import BaseSchema, TimestampMixin


class UserBase(BaseSchema):
    """Base user schema with common fields."""

    email: EmailStr = Field(
        ...,
        description="User's email address",
        examples=["auditor@company.com"],
    )
    full_name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="User's full name",
        examples=["John Doe"],
    )
    department: str | None = Field(
        default=None,
        max_length=100,
        description="User's department",
        examples=["Internal Audit"],
    )
    is_active: bool = Field(
        default=True,
        description="Whether the user account is active",
    )


class UserCreate(UserBase):
    """Schema for creating a new user."""

    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="User's password (min 8 characters)",
        examples=["SecureP@ssw0rd!"],
    )


class UserUpdate(BaseSchema):
    """Schema for updating a user. All fields are optional."""

    email: EmailStr | None = Field(
        default=None,
        description="User's email address",
        examples=["auditor@company.com"],
    )
    full_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="User's full name",
        examples=["John Doe"],
    )
    department: str | None = Field(
        default=None,
        max_length=100,
        description="User's department",
        examples=["Internal Audit"],
    )
    is_active: bool | None = Field(
        default=None,
        description="Whether the user account is active",
    )
    password: str | None = Field(
        default=None,
        min_length=8,
        max_length=128,
        description="New password (min 8 characters)",
    )


class UserResponse(UserBase, TimestampMixin):
    """Schema for user response."""

    id: UUID = Field(
        ...,
        description="Unique user identifier",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "email": "auditor@company.com",
                "full_name": "John Doe",
                "department": "Internal Audit",
                "is_active": True,
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z",
            }
        },
    }


class UserBrief(BaseSchema):
    """Brief user info for embedding in other responses."""

    id: UUID
    full_name: str
    email: EmailStr
