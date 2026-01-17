"""Notification router for user notifications."""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi import status as http_status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.routers.auth import get_current_user_required
from app.schemas.common import MessageResponse
from app.schemas.workflow import (
    NotificationCountResponse,
    NotificationListResponse,
    NotificationMarkReadResponse,
    NotificationResponse,
)
from app.services.notification_service import notification_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notifications", tags=["notifications"])

# Type aliases
DbSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[dict, Depends(get_current_user_required)]


@router.get(
    "",
    response_model=NotificationListResponse,
    summary="Get current user's notifications",
)
async def list_notifications(
    db: DbSession,
    current_user: CurrentUser,
    unread_only: bool = Query(False, description="Only return unread notifications"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
) -> NotificationListResponse:
    """
    Get notifications for the current user.

    Returns paginated list of notifications, optionally filtered to only unread.
    """
    skip = (page - 1) * page_size
    user_id = current_user["id"]

    notifications, total = await notification_service.get_user_notifications(
        db=db,
        user_id=user_id,
        unread_only=unread_only,
        skip=skip,
        limit=page_size,
    )

    total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0

    return NotificationListResponse(
        items=notifications,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get(
    "/unread-count",
    response_model=NotificationCountResponse,
    summary="Get unread notification count",
)
async def get_unread_count(
    db: DbSession,
    current_user: CurrentUser,
) -> NotificationCountResponse:
    """
    Get count of unread notifications for the current user.
    """
    user_id = current_user["id"]
    count = await notification_service.get_unread_count(db=db, user_id=user_id)

    return NotificationCountResponse(count=count)


@router.get(
    "/{notification_id}",
    response_model=NotificationResponse,
    summary="Get a notification by ID",
)
async def get_notification(
    notification_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> NotificationResponse:
    """
    Get a specific notification by ID.

    Only returns the notification if it belongs to the current user.
    """
    user_id = current_user["id"]
    notification = await notification_service.get_notification_by_id(
        db=db,
        notification_id=notification_id,
        user_id=user_id,
    )

    if not notification:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )

    return NotificationResponse(**notification)


@router.patch(
    "/{notification_id}/read",
    response_model=MessageResponse,
    summary="Mark notification as read",
)
async def mark_as_read(
    notification_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> MessageResponse:
    """
    Mark a specific notification as read.
    """
    user_id = current_user["id"]
    success = await notification_service.mark_as_read(
        db=db,
        notification_id=notification_id,
        user_id=user_id,
    )

    if not success:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Notification not found or already read",
        )

    return MessageResponse(message="Notification marked as read")


@router.post(
    "/mark-all-read",
    response_model=NotificationMarkReadResponse,
    summary="Mark all notifications as read",
)
async def mark_all_as_read(
    db: DbSession,
    current_user: CurrentUser,
) -> NotificationMarkReadResponse:
    """
    Mark all notifications for the current user as read.
    """
    user_id = current_user["id"]
    marked_count = await notification_service.mark_all_as_read(db=db, user_id=user_id)

    return NotificationMarkReadResponse(marked_count=marked_count)


@router.delete(
    "/{notification_id}",
    response_model=MessageResponse,
    summary="Delete a notification",
)
async def delete_notification(
    notification_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> MessageResponse:
    """
    Delete a specific notification.
    """
    user_id = current_user["id"]
    success = await notification_service.delete_notification(
        db=db,
        notification_id=notification_id,
        user_id=user_id,
    )

    if not success:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )

    return MessageResponse(message="Notification deleted")
