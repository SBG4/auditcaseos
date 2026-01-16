"""Notification service for managing user notifications."""

import json
import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for creating and managing user notifications."""

    async def create_notification(
        self,
        db: AsyncSession,
        user_id: UUID | str,
        title: str,
        message: str,
        priority: str = "NORMAL",
        entity_type: str | None = None,
        entity_id: UUID | str | None = None,
        link_url: str | None = None,
        source: str = "system",
        source_rule_id: UUID | str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Create a new notification for a user.

        Args:
            db: Database session
            user_id: Recipient user ID
            title: Notification title
            message: Notification message
            priority: Priority level (LOW, NORMAL, HIGH, URGENT)
            entity_type: Related entity type (case, evidence, etc.)
            entity_id: Related entity ID
            link_url: URL to navigate when clicked
            source: What created the notification (workflow, system, user)
            source_rule_id: Workflow rule that created this (if applicable)
            metadata: Additional metadata

        Returns:
            Created notification dict
        """
        try:
            query = text("""
                INSERT INTO notifications (
                    user_id, title, message, priority,
                    entity_type, entity_id, link_url,
                    source, source_rule_id, metadata
                ) VALUES (
                    :user_id, :title, :message, CAST(:priority AS notification_priority),
                    :entity_type, :entity_id, :link_url,
                    :source, :source_rule_id, CAST(:metadata AS jsonb)
                )
                RETURNING *
            """)

            params = {
                "user_id": str(user_id),
                "title": title,
                "message": message,
                "priority": priority,
                "entity_type": entity_type,
                "entity_id": str(entity_id) if entity_id else None,
                "link_url": link_url,
                "source": source,
                "source_rule_id": str(source_rule_id) if source_rule_id else None,
                "metadata": json.dumps(metadata) if metadata else "{}",
            }

            result = await db.execute(query, params)
            await db.commit()
            row = result.fetchone()

            if row:
                notification = dict(row._mapping)
                logger.debug(f"Created notification {notification['id']} for user {user_id}")

                # Broadcast via WebSocket (non-blocking)
                try:
                    from app.services.websocket_service import connection_manager
                    await connection_manager.send_notification(
                        user_id=str(user_id),
                        notification_data={
                            "id": str(notification["id"]),
                            "title": notification["title"],
                            "message": notification["message"],
                            "priority": str(notification["priority"]),
                            "entity_type": notification.get("entity_type"),
                            "link_url": notification.get("link_url"),
                            "created_at": notification["created_at"].isoformat() if notification.get("created_at") else None,
                        },
                    )
                except Exception as ws_error:
                    logger.debug(f"WebSocket notification broadcast skipped: {ws_error}")

                return notification

            raise Exception("Failed to create notification")

        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to create notification: {e}")
            raise

    async def create_bulk_notifications(
        self,
        db: AsyncSession,
        notifications: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Create multiple notifications at once.

        Args:
            db: Database session
            notifications: List of notification dicts with keys:
                - user_id (required)
                - title (required)
                - message (required)
                - priority, entity_type, entity_id, link_url, source, source_rule_id, metadata

        Returns:
            List of created notification dicts
        """
        created = []
        for notif_data in notifications:
            try:
                notification = await self.create_notification(
                    db=db,
                    user_id=notif_data["user_id"],
                    title=notif_data["title"],
                    message=notif_data["message"],
                    priority=notif_data.get("priority", "NORMAL"),
                    entity_type=notif_data.get("entity_type"),
                    entity_id=notif_data.get("entity_id"),
                    link_url=notif_data.get("link_url"),
                    source=notif_data.get("source", "system"),
                    source_rule_id=notif_data.get("source_rule_id"),
                    metadata=notif_data.get("metadata"),
                )
                created.append(notification)
            except Exception as e:
                logger.error(f"Failed to create notification for user {notif_data.get('user_id')}: {e}")

        return created

    async def get_user_notifications(
        self,
        db: AsyncSession,
        user_id: UUID | str,
        unread_only: bool = False,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[dict[str, Any]], int]:
        """
        Get notifications for a user.

        Args:
            db: Database session
            user_id: User ID
            unread_only: Only return unread notifications
            skip: Number of notifications to skip
            limit: Maximum notifications to return

        Returns:
            Tuple of (list of notification dicts, total count)
        """
        try:
            # Build WHERE clause
            where_clause = "user_id = :user_id"
            if unread_only:
                where_clause += " AND is_read = false"

            # Count query
            count_query = text(f"""
                SELECT COUNT(*) as count FROM notifications
                WHERE {where_clause}
            """)
            count_result = await db.execute(count_query, {"user_id": str(user_id)})
            total = count_result.scalar() or 0

            # Main query
            query = text(f"""
                SELECT * FROM notifications
                WHERE {where_clause}
                ORDER BY created_at DESC
                OFFSET :skip LIMIT :limit
            """)

            result = await db.execute(query, {
                "user_id": str(user_id),
                "skip": skip,
                "limit": limit,
            })

            notifications = [dict(row._mapping) for row in result.fetchall()]
            return notifications, total

        except Exception as e:
            logger.error(f"Failed to get notifications for user {user_id}: {e}")
            raise

    async def get_unread_count(
        self,
        db: AsyncSession,
        user_id: UUID | str,
    ) -> int:
        """
        Get count of unread notifications for a user.

        Args:
            db: Database session
            user_id: User ID

        Returns:
            Number of unread notifications
        """
        try:
            query = text("""
                SELECT COUNT(*) as count FROM notifications
                WHERE user_id = :user_id AND is_read = false
            """)

            result = await db.execute(query, {"user_id": str(user_id)})
            return result.scalar() or 0

        except Exception as e:
            logger.error(f"Failed to get unread count for user {user_id}: {e}")
            raise

    async def mark_as_read(
        self,
        db: AsyncSession,
        notification_id: UUID | str,
        user_id: UUID | str,
    ) -> bool:
        """
        Mark a notification as read.

        Args:
            db: Database session
            notification_id: Notification ID
            user_id: User ID (for ownership verification)

        Returns:
            True if marked, False if not found or not owned by user
        """
        try:
            query = text("""
                UPDATE notifications
                SET is_read = true, read_at = :read_at
                WHERE id = :notification_id AND user_id = :user_id AND is_read = false
                RETURNING id
            """)

            result = await db.execute(query, {
                "notification_id": str(notification_id),
                "user_id": str(user_id),
                "read_at": datetime.utcnow(),
            })
            await db.commit()

            return result.fetchone() is not None

        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to mark notification {notification_id} as read: {e}")
            raise

    async def mark_all_as_read(
        self,
        db: AsyncSession,
        user_id: UUID | str,
    ) -> int:
        """
        Mark all notifications for a user as read.

        Args:
            db: Database session
            user_id: User ID

        Returns:
            Number of notifications marked as read
        """
        try:
            query = text("""
                UPDATE notifications
                SET is_read = true, read_at = :read_at
                WHERE user_id = :user_id AND is_read = false
            """)

            result = await db.execute(query, {
                "user_id": str(user_id),
                "read_at": datetime.utcnow(),
            })
            await db.commit()

            return result.rowcount

        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to mark all notifications as read for user {user_id}: {e}")
            raise

    async def delete_notification(
        self,
        db: AsyncSession,
        notification_id: UUID | str,
        user_id: UUID | str,
    ) -> bool:
        """
        Delete a notification.

        Args:
            db: Database session
            notification_id: Notification ID
            user_id: User ID (for ownership verification)

        Returns:
            True if deleted, False if not found or not owned by user
        """
        try:
            query = text("""
                DELETE FROM notifications
                WHERE id = :notification_id AND user_id = :user_id
                RETURNING id
            """)

            result = await db.execute(query, {
                "notification_id": str(notification_id),
                "user_id": str(user_id),
            })
            await db.commit()

            return result.fetchone() is not None

        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to delete notification {notification_id}: {e}")
            raise

    async def delete_old_notifications(
        self,
        db: AsyncSession,
        days: int = 30,
    ) -> int:
        """
        Delete notifications older than specified days.

        Args:
            db: Database session
            days: Number of days after which to delete notifications

        Returns:
            Number of notifications deleted
        """
        try:
            query = text("""
                DELETE FROM notifications
                WHERE created_at < CURRENT_TIMESTAMP - INTERVAL ':days days'
            """)

            result = await db.execute(query, {"days": days})
            await db.commit()

            deleted = result.rowcount
            if deleted > 0:
                logger.info(f"Deleted {deleted} notifications older than {days} days")
            return deleted

        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to delete old notifications: {e}")
            raise

    async def get_notification_by_id(
        self,
        db: AsyncSession,
        notification_id: UUID | str,
        user_id: UUID | str | None = None,
    ) -> dict[str, Any] | None:
        """
        Get a notification by ID.

        Args:
            db: Database session
            notification_id: Notification ID
            user_id: Optional user ID for ownership verification

        Returns:
            Notification dict or None if not found
        """
        try:
            where_clause = "id = :notification_id"
            params: dict[str, Any] = {"notification_id": str(notification_id)}

            if user_id:
                where_clause += " AND user_id = :user_id"
                params["user_id"] = str(user_id)

            query = text(f"""
                SELECT * FROM notifications
                WHERE {where_clause}
            """)

            result = await db.execute(query, params)
            row = result.fetchone()

            return dict(row._mapping) if row else None

        except Exception as e:
            logger.error(f"Failed to get notification {notification_id}: {e}")
            raise


# Singleton instance
notification_service = NotificationService()
