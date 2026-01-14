"""Users router for AuditCaseOS API.

This module provides endpoints for user management including
CRUD operations and current user retrieval.
"""

from datetime import datetime
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.common import BaseSchema, MessageResponse, PaginatedResponse, TimestampMixin

router = APIRouter(prefix="/users", tags=["users"])


# =============================================================================
# Schemas
# =============================================================================


class UserRole(str):
    """User role constants."""

    ADMIN = "admin"
    AUDITOR = "auditor"
    REVIEWER = "reviewer"
    VIEWER = "viewer"


class UserBase(BaseSchema):
    """Base schema for user data."""

    email: EmailStr = Field(..., description="User email address")
    full_name: str = Field(..., min_length=1, max_length=255, description="User's full name")
    department: str | None = Field(None, max_length=100, description="User's department")
    role: str = Field(default="viewer", description="User role")
    is_active: bool = Field(default=True, description="Whether user account is active")


class UserCreate(UserBase):
    """Schema for creating a new user."""

    password: str = Field(..., min_length=8, description="User password")


class UserUpdate(BaseSchema):
    """Schema for updating a user."""

    email: EmailStr | None = None
    full_name: str | None = Field(None, min_length=1, max_length=255)
    department: str | None = Field(None, max_length=100)
    role: str | None = None
    is_active: bool | None = None


class UserResponse(UserBase, TimestampMixin):
    """Schema for user response."""

    id: UUID = Field(..., description="User UUID")


class UserListResponse(PaginatedResponse):
    """Paginated list of users."""

    items: list[UserResponse]


class CurrentUserResponse(UserResponse):
    """Schema for current user response with additional details."""

    permissions: list[str] = Field(default_factory=list, description="User permissions")


# =============================================================================
# Dependencies
# =============================================================================


def get_current_user_id() -> UUID:
    """
    Dependency to get current user ID from authentication.

    This is a placeholder for authentication.

    Returns:
        UUID: Current user's UUID
    """
    # TODO: Implement actual authentication (JWT, OAuth, etc.)
    return UUID("00000000-0000-0000-0000-000000000001")


# Type aliases for dependency injection
DbSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUserId = Annotated[UUID, Depends(get_current_user_id)]


# =============================================================================
# Endpoints
# =============================================================================


@router.get(
    "/me",
    response_model=CurrentUserResponse,
    summary="Get current user",
    description="Retrieve the currently authenticated user's profile.",
)
async def get_current_user() -> CurrentUserResponse:
    """
    Get the current authenticated user's profile.

    Returns the user's profile information along with their
    permissions and role details.

    This endpoint requires authentication.

    Returns:
        CurrentUserResponse: Current user's profile with permissions
    """
    # TODO: Implement actual user retrieval from authentication context
    # Placeholder response
    now = datetime.utcnow()
    return CurrentUserResponse(
        id=get_current_user_id(),
        email="placeholder@example.com",
        full_name="Placeholder User",
        department="Audit",
        role="auditor",
        is_active=True,
        permissions=["cases:read", "cases:write", "evidence:read", "evidence:write"],
        created_at=now,
        updated_at=now,
    )


@router.get(
    "/",
    response_model=UserListResponse,
    summary="List all users",
    description="Retrieve a paginated list of all users.",
)
async def list_users(
    search: str | None = Query(None, description="Search in name and email"),
    role: str | None = Query(None, description="Filter by role"),
    is_active: bool | None = Query(None, description="Filter by active status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
) -> UserListResponse:
    """
    List all users with filtering and pagination.

    - **search**: Search term to match against name and email
    - **role**: Filter by user role
    - **is_active**: Filter by active/inactive status
    - **page**: Page number (starts at 1)
    - **page_size**: Number of items per page (max 100)

    Requires admin role to access.

    Returns a paginated list of users matching the filters.
    """
    # TODO: Implement actual database query
    return UserListResponse(
        items=[],
        total=0,
        page=page,
        page_size=page_size,
        total_pages=0,
    )


@router.post(
    "/",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user",
    description="Create a new user account.",
)
async def create_user(
    user_data: UserCreate,
) -> UserResponse:
    """
    Create a new user account.

    - **email**: User's email address (must be unique)
    - **full_name**: User's full name
    - **department**: Optional department
    - **role**: User role (admin, auditor, reviewer, viewer)
    - **password**: User password (min 8 characters)

    Requires admin role to create users.

    Returns the created user (without password).

    Raises:
        HTTPException: 400 if email already exists
    """
    # TODO: Implement actual user creation
    # 1. Check if email exists
    # 2. Hash password
    # 3. Create user in database

    now = datetime.utcnow()
    return UserResponse(
        id=uuid4(),
        email=user_data.email,
        full_name=user_data.full_name,
        department=user_data.department,
        role=user_data.role,
        is_active=user_data.is_active,
        created_at=now,
        updated_at=now,
    )


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Get user by ID",
    description="Retrieve a specific user by their ID.",
)
async def get_user(
    user_id: UUID,
) -> UserResponse:
    """
    Get a specific user by their UUID.

    Returns the user's profile information.

    Raises:
        HTTPException: 404 if user not found
    """
    # TODO: Implement actual database query
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"User with ID '{user_id}' not found",
    )


@router.patch(
    "/{user_id}",
    response_model=UserResponse,
    summary="Update user",
    description="Update an existing user's details.",
)
async def update_user(
    user_id: UUID,
    user_update: UserUpdate,
) -> UserResponse:
    """
    Update an existing user's profile.

    Only provided fields will be updated. All fields are optional.

    - **email**: Update email address
    - **full_name**: Update full name
    - **department**: Update department
    - **role**: Update role
    - **is_active**: Activate/deactivate account

    Requires admin role or ownership of the account.

    Returns the updated user.

    Raises:
        HTTPException: 404 if user not found
        HTTPException: 400 if email already exists
    """
    # TODO: Implement actual database update
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"User with ID '{user_id}' not found",
    )


@router.delete(
    "/{user_id}",
    response_model=MessageResponse,
    summary="Delete user",
    description="Delete a user account.",
)
async def delete_user(
    user_id: UUID,
) -> MessageResponse:
    """
    Delete a user account.

    This deactivates the user account rather than permanently deleting it.
    The user's data is preserved for audit purposes.

    Requires admin role.

    Returns a confirmation message.

    Raises:
        HTTPException: 404 if user not found
        HTTPException: 400 if trying to delete own account
    """
    # TODO: Implement actual user deactivation
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"User with ID '{user_id}' not found",
    )
