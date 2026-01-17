"""Authentication router for AuditCaseOS API.

This module provides endpoints for user authentication, including
login, token refresh, and user registration (admin only).

Rate Limiting:
- Login: 10 requests/minute (brute force protection)
- Register: 5 requests/minute (spam protection)
- Password change: 5 requests/minute
- Other endpoints: Default rate limit

Source: OWASP API Security Top 10 - API4:2023 Unrestricted Resource Consumption
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi import status as http_status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.schemas.common import BaseSchema, MessageResponse
from app.services.audit_service import audit_service
from app.services.auth_service import auth_service
from app.utils.rate_limit import AUTH_RATE_LIMIT, limiter
from app.utils.security import decode_access_token

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/auth", tags=["authentication"])

# OAuth2 scheme for token extraction
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


# =============================================================================
# Schemas
# =============================================================================


class Token(BaseSchema):
    """Schema for authentication token response."""

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")


class TokenWithUser(Token):
    """Token response with user information."""

    user_id: str = Field(..., description="User UUID")
    username: str = Field(..., description="Username")
    email: str = Field(..., description="User email")
    role: str = Field(..., description="User role")
    full_name: str = Field(..., description="User's full name")


class UserCreate(BaseSchema):
    """Schema for creating a new user."""

    username: str = Field(..., min_length=3, max_length=100, description="Unique username")
    email: EmailStr = Field(..., description="Email address")
    password: str = Field(..., min_length=8, max_length=100, description="Password (min 8 chars)")
    full_name: str = Field(..., min_length=1, max_length=255, description="Full name")
    role: str = Field(default="viewer", pattern="^(admin|auditor|reviewer|viewer)$", description="User role")
    department: str | None = Field(None, max_length=100, description="Department")


class UserResponse(BaseSchema):
    """Schema for user response (no password)."""

    id: str = Field(..., description="User UUID")
    username: str = Field(..., description="Username")
    email: str = Field(..., description="Email address")
    full_name: str = Field(..., description="Full name")
    role: str = Field(..., description="User role")
    department: str | None = Field(None, description="Department")
    is_active: bool = Field(..., description="Whether user is active")


class PasswordChange(BaseSchema):
    """Schema for password change request."""

    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, max_length=100, description="New password")


# =============================================================================
# Dependencies
# =============================================================================


DbSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    db: DbSession,
    token: str | None = Depends(oauth2_scheme),
) -> dict | None:
    """
    Dependency to get current authenticated user from JWT token.

    Args:
        db: Database session
        token: JWT token from Authorization header

    Returns:
        User dict if authenticated, None if no token

    Raises:
        HTTPException: If token is invalid or user not found
    """
    if token is None:
        return None

    token_data = decode_access_token(token)
    if token_data is None:
        raise HTTPException(
            status_code=http_status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await auth_service.get_user_by_id(db, token_data.user_id)
    if user is None:
        raise HTTPException(
            status_code=http_status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.get("is_active", False):
        raise HTTPException(
            status_code=http_status.HTTP_401_UNAUTHORIZED,
            detail="User account is disabled",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_current_user_required(
    user: dict | None = Depends(get_current_user),
) -> dict:
    """
    Dependency that requires authentication.

    Raises HTTPException if not authenticated.
    """
    if user is None:
        raise HTTPException(
            status_code=http_status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def get_admin_user(
    user: dict = Depends(get_current_user_required),
) -> dict:
    """
    Dependency that requires admin role.

    Raises HTTPException if not admin.
    """
    if str(user.get("role")) != "admin":
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user


# Type aliases
CurrentUser = Annotated[dict, Depends(get_current_user_required)]
AdminUser = Annotated[dict, Depends(get_admin_user)]
OptionalUser = Annotated[dict | None, Depends(get_current_user)]


# =============================================================================
# Endpoints
# =============================================================================


@router.post(
    "/login",
    response_model=TokenWithUser,
    summary="Login and get access token",
    description="Authenticate with username/email and password to receive a JWT access token.",
)
@limiter.limit(AUTH_RATE_LIMIT)
async def login(
    request: Request,
    db: DbSession,
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> TokenWithUser:
    """
    Login endpoint using OAuth2 password flow.

    Accepts username or email in the 'username' field.
    Returns JWT access token on successful authentication.
    """
    user = await auth_service.authenticate_user(
        db=db,
        username=form_data.username,
        password=form_data.password,
    )

    if not user:
        # Log failed login attempt
        client_ip = request.client.host if request.client else None
        try:
            await audit_service.log_login(
                db=db,
                user_id=None,
                success=False,
                user_ip=client_ip,
                username=form_data.username,
            )
        except Exception:
            pass  # Don't fail login on audit log error

        raise HTTPException(
            status_code=http_status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create access token
    access_token = auth_service.create_user_token(user)

    # Log successful login
    client_ip = request.client.host if request.client else None
    try:
        await audit_service.log_login(
            db=db,
            user_id=user["id"],
            success=True,
            user_ip=client_ip,
            username=user["username"],
        )
    except Exception as e:
        logger.warning(f"Failed to log login: {e}")

    return TokenWithUser(
        access_token=access_token,
        token_type="bearer",
        user_id=str(user["id"]),
        username=user["username"],
        email=user["email"],
        role=str(user["role"]),
        full_name=user["full_name"],
    )


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=http_status.HTTP_201_CREATED,
    summary="Register a new user (admin only)",
    description="Create a new user account. Requires admin privileges.",
)
@limiter.limit("5/minute")
async def register(
    request: Request,
    db: DbSession,
    user_data: UserCreate,
    admin: AdminUser,
) -> UserResponse:
    """
    Register a new user (admin only).

    Creates a new user account with the specified details.
    Only administrators can create new users.
    """
    try:
        user = await auth_service.create_user(
            db=db,
            username=user_data.username,
            email=user_data.email,
            password=user_data.password,
            full_name=user_data.full_name,
            role=user_data.role,
            department=user_data.department,
        )

        # Log user creation
        client_ip = request.client.host if request.client else None
        try:
            await audit_service.log_create(
                db=db,
                entity_type="user",
                entity_id=user["id"],
                user_id=admin["id"],
                new_values={"username": user["username"], "email": user["email"], "role": user["role"]},
                user_ip=client_ip,
            )
        except Exception as e:
            logger.warning(f"Failed to log user creation: {e}")

        return UserResponse(
            id=str(user["id"]),
            username=user["username"],
            email=user["email"],
            full_name=user["full_name"],
            role=str(user["role"]),
            department=user.get("department"),
            is_active=user.get("is_active", True),
        )

    except ValueError as e:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to register user: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user",
        )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
    description="Returns the profile of the currently authenticated user.",
)
async def get_me(
    current_user: CurrentUser,
) -> UserResponse:
    """Get the current authenticated user's profile."""
    return UserResponse(
        id=str(current_user["id"]),
        username=current_user["username"],
        email=current_user["email"],
        full_name=current_user["full_name"],
        role=str(current_user["role"]),
        department=current_user.get("department"),
        is_active=current_user.get("is_active", True),
    )


@router.post(
    "/change-password",
    response_model=MessageResponse,
    summary="Change password",
    description="Change the current user's password.",
)
@limiter.limit("5/minute")
async def change_password(
    request: Request,
    db: DbSession,
    password_data: PasswordChange,
    current_user: CurrentUser,
) -> MessageResponse:
    """Change the current user's password."""
    # Verify current password
    user = await auth_service.authenticate_user(
        db=db,
        username=current_user["username"],
        password=password_data.current_password,
    )

    if not user:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    # Update password
    success = await auth_service.update_password(
        db=db,
        user_id=current_user["id"],
        new_password=password_data.new_password,
    )

    if not success:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update password",
        )

    # Log password change
    client_ip = request.client.host if request.client else None
    try:
        await audit_service.log_action(
            db=db,
            action="PASSWORD_CHANGE",
            entity_type="user",
            entity_id=current_user["id"],
            user_id=current_user["id"],
            user_ip=client_ip,
        )
    except Exception as e:
        logger.warning(f"Failed to log password change: {e}")

    return MessageResponse(message="Password changed successfully")


class UserUpdate(BaseSchema):
    """Schema for updating a user."""

    email: EmailStr | None = None
    full_name: str | None = Field(None, min_length=1, max_length=255)
    role: str | None = Field(None, pattern="^(admin|auditor|reviewer|viewer)$")
    department: str | None = Field(None, max_length=100)
    is_active: bool | None = None


class UsersListResponse(BaseSchema):
    """Paginated users list response."""

    items: list[UserResponse]
    total: int
    skip: int
    limit: int


@router.get(
    "/users",
    response_model=UsersListResponse,
    summary="List all users (admin only)",
    description="Returns a paginated list of all users. Requires admin privileges.",
)
async def list_users(
    db: DbSession,
    admin: AdminUser,
    skip: int = 0,
    limit: int = 50,
) -> UsersListResponse:
    """List all users (admin only)."""
    users = await auth_service.list_users(db, skip=skip, limit=limit)
    total = await auth_service.count_users(db)

    return UsersListResponse(
        items=[
            UserResponse(
                id=str(user["id"]),
                username=user["username"],
                email=user["email"],
                full_name=user["full_name"],
                role=str(user["role"]),
                department=user.get("department"),
                is_active=user.get("is_active", True),
            )
            for user in users
        ],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/users/{user_id}",
    response_model=UserResponse,
    summary="Get user by ID (admin only)",
    description="Returns a specific user by ID. Requires admin privileges.",
)
async def get_user(
    db: DbSession,
    user_id: str,
    admin: AdminUser,
) -> UserResponse:
    """Get a user by ID (admin only)."""
    user = await auth_service.get_user_by_id(db, user_id)

    if not user:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return UserResponse(
        id=str(user["id"]),
        username=user["username"],
        email=user["email"],
        full_name=user["full_name"],
        role=str(user["role"]),
        department=user.get("department"),
        is_active=user.get("is_active", True),
    )


@router.patch(
    "/users/{user_id}",
    response_model=UserResponse,
    summary="Update user (admin only)",
    description="Update a user's profile. Requires admin privileges.",
)
async def update_user(
    db: DbSession,
    request: Request,
    user_id: str,
    user_data: UserUpdate,
    admin: AdminUser,
) -> UserResponse:
    """Update a user (admin only)."""
    try:
        user = await auth_service.update_user(
            db=db,
            user_id=user_id,
            email=user_data.email,
            full_name=user_data.full_name,
            role=user_data.role,
            department=user_data.department,
            is_active=user_data.is_active,
        )

        if not user:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        # Log user update
        client_ip = request.client.host if request.client else None
        try:
            await audit_service.log_action(
                db=db,
                action="UPDATE",
                entity_type="user",
                entity_id=user_id,
                user_id=admin["id"],
                new_values=user_data.model_dump(exclude_none=True),
                user_ip=client_ip,
            )
        except Exception as e:
            logger.warning(f"Failed to log user update: {e}")

        return UserResponse(
            id=str(user["id"]),
            username=user["username"],
            email=user["email"],
            full_name=user["full_name"],
            role=str(user["role"]),
            department=user.get("department"),
            is_active=user.get("is_active", True),
        )

    except ValueError as e:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete(
    "/users/{user_id}",
    response_model=MessageResponse,
    summary="Deactivate user (admin only)",
    description="Deactivate a user account. Requires admin privileges.",
)
async def deactivate_user(
    db: DbSession,
    request: Request,
    user_id: str,
    admin: AdminUser,
) -> MessageResponse:
    """Deactivate a user (admin only). Cannot deactivate yourself."""
    # Prevent self-deactivation
    if str(admin["id"]) == user_id:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account",
        )

    success = await auth_service.deactivate_user(db, user_id)

    if not success:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Log user deactivation
    client_ip = request.client.host if request.client else None
    try:
        await audit_service.log_action(
            db=db,
            action="DEACTIVATE",
            entity_type="user",
            entity_id=user_id,
            user_id=admin["id"],
            user_ip=client_ip,
        )
    except Exception as e:
        logger.warning(f"Failed to log user deactivation: {e}")

    return MessageResponse(message="User deactivated successfully")
