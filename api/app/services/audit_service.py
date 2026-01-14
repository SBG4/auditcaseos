"""Audit service for logging all actions in the system."""

import logging
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class AuditService:
    """Service for logging audit trail of all system actions."""

    async def log_action(
        self,
        db: AsyncSession,
        action: str,
        entity_type: str,
        entity_id: UUID | str | None,
        user_id: UUID | str | None,
        old_values: dict[str, Any] | None = None,
        new_values: dict[str, Any] | None = None,
        user_ip: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Log an action to the audit log.

        Args:
            db: Database session
            action: Action type (e.g., 'CREATE', 'UPDATE', 'DELETE', 'VIEW', 'DOWNLOAD')
            entity_type: Type of entity (e.g., 'case', 'evidence', 'finding', 'user')
            entity_id: ID of the affected entity (optional)
            user_id: ID of the user performing the action (optional)
            old_values: Previous values before change (for updates/deletes)
            new_values: New values after change (for creates/updates)
            user_ip: IP address of the user (optional)
            metadata: Additional metadata about the action (optional)

        Returns:
            None

        Raises:
            Exception: If logging fails
        """
        try:
            import json

            query = text("""
                INSERT INTO audit_log (
                    action, entity_type, entity_id, user_id, user_ip,
                    old_values, new_values, metadata
                ) VALUES (
                    :action, :entity_type, :entity_id, :user_id, :user_ip,
                    CAST(:old_values AS jsonb), CAST(:new_values AS jsonb), CAST(:metadata AS jsonb)
                )
            """)

            # Serialize dicts to JSON strings for JSONB casting
            old_values_json = json.dumps(old_values) if old_values else None
            new_values_json = json.dumps(new_values) if new_values else None
            metadata_json = json.dumps(metadata) if metadata else "{}"

            params = {
                "action": action,
                "entity_type": entity_type,
                "entity_id": str(entity_id) if entity_id else None,
                "user_id": str(user_id) if user_id else None,
                "user_ip": user_ip,
                "old_values": old_values_json,
                "new_values": new_values_json,
                "metadata": metadata_json,
            }

            await db.execute(query, params)
            await db.commit()

            logger.debug(
                f"Audit log: {action} {entity_type} {entity_id} by user {user_id}"
            )

        except Exception as e:
            # Don't rollback here - audit logging should not affect the main transaction
            # Just log the error and continue
            logger.error(
                f"Failed to log audit action: {action} {entity_type} {entity_id} - {e}"
            )
            # Re-raise to let caller decide how to handle
            raise

    async def log_create(
        self,
        db: AsyncSession,
        entity_type: str,
        entity_id: UUID | str,
        user_id: UUID | str,
        new_values: dict[str, Any],
        user_ip: str | None = None,
    ) -> None:
        """
        Log a create action.

        Args:
            db: Database session
            entity_type: Type of entity created
            entity_id: ID of the created entity
            user_id: ID of the user who created it
            new_values: The created entity values
            user_ip: IP address of the user
        """
        await self.log_action(
            db=db,
            action="CREATE",
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=user_id,
            old_values=None,
            new_values=new_values,
            user_ip=user_ip,
        )

    async def log_update(
        self,
        db: AsyncSession,
        entity_type: str,
        entity_id: UUID | str,
        user_id: UUID | str,
        old_values: dict[str, Any],
        new_values: dict[str, Any],
        user_ip: str | None = None,
    ) -> None:
        """
        Log an update action.

        Args:
            db: Database session
            entity_type: Type of entity updated
            entity_id: ID of the updated entity
            user_id: ID of the user who updated it
            old_values: Values before the update
            new_values: Values after the update
            user_ip: IP address of the user
        """
        await self.log_action(
            db=db,
            action="UPDATE",
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=user_id,
            old_values=old_values,
            new_values=new_values,
            user_ip=user_ip,
        )

    async def log_delete(
        self,
        db: AsyncSession,
        entity_type: str,
        entity_id: UUID | str,
        user_id: UUID | str,
        old_values: dict[str, Any],
        user_ip: str | None = None,
    ) -> None:
        """
        Log a delete action.

        Args:
            db: Database session
            entity_type: Type of entity deleted
            entity_id: ID of the deleted entity
            user_id: ID of the user who deleted it
            old_values: Values before deletion
            user_ip: IP address of the user
        """
        await self.log_action(
            db=db,
            action="DELETE",
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=user_id,
            old_values=old_values,
            new_values=None,
            user_ip=user_ip,
        )

    async def log_view(
        self,
        db: AsyncSession,
        entity_type: str,
        entity_id: UUID | str,
        user_id: UUID | str,
        user_ip: str | None = None,
    ) -> None:
        """
        Log a view action.

        Args:
            db: Database session
            entity_type: Type of entity viewed
            entity_id: ID of the viewed entity
            user_id: ID of the user who viewed it
            user_ip: IP address of the user
        """
        await self.log_action(
            db=db,
            action="VIEW",
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=user_id,
            user_ip=user_ip,
        )

    async def log_download(
        self,
        db: AsyncSession,
        entity_type: str,
        entity_id: UUID | str,
        user_id: UUID | str,
        file_path: str | None = None,
        user_ip: str | None = None,
    ) -> None:
        """
        Log a download action.

        Args:
            db: Database session
            entity_type: Type of entity downloaded
            entity_id: ID of the downloaded entity
            user_id: ID of the user who downloaded it
            file_path: Path of the downloaded file
            user_ip: IP address of the user
        """
        metadata = {"file_path": file_path} if file_path else None
        await self.log_action(
            db=db,
            action="DOWNLOAD",
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=user_id,
            metadata=metadata,
            user_ip=user_ip,
        )

    async def log_login(
        self,
        db: AsyncSession,
        user_id: UUID | str,
        success: bool,
        user_ip: str | None = None,
        username: str | None = None,
    ) -> None:
        """
        Log a login attempt.

        Args:
            db: Database session
            user_id: ID of the user (if known)
            success: Whether login was successful
            user_ip: IP address of the user
            username: Username attempted
        """
        action = "LOGIN_SUCCESS" if success else "LOGIN_FAILURE"
        metadata = {"username": username} if username else None

        await self.log_action(
            db=db,
            action=action,
            entity_type="user",
            entity_id=user_id,
            user_id=user_id,
            metadata=metadata,
            user_ip=user_ip,
        )

    async def get_entity_history(
        self,
        db: AsyncSession,
        entity_type: str,
        entity_id: UUID | str,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """
        Get audit history for a specific entity.

        Args:
            db: Database session
            entity_type: Type of entity
            entity_id: ID of the entity
            limit: Maximum number of records to return

        Returns:
            List of audit log entries
        """
        try:
            query = text("""
                SELECT
                    id, action, entity_type, entity_id, user_id, user_ip,
                    old_values, new_values, metadata, created_at
                FROM audit_log
                WHERE entity_type = :entity_type AND entity_id = :entity_id
                ORDER BY created_at DESC
                LIMIT :limit
            """)

            result = await db.execute(
                query,
                {
                    "entity_type": entity_type,
                    "entity_id": str(entity_id),
                    "limit": limit,
                },
            )
            rows = result.fetchall()

            return [dict(row._mapping) for row in rows]

        except Exception as e:
            logger.error(f"Failed to get entity history: {e}")
            raise

    async def get_user_activity(
        self,
        db: AsyncSession,
        user_id: UUID | str,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """
        Get audit history for a specific user's actions.

        Args:
            db: Database session
            user_id: ID of the user
            limit: Maximum number of records to return

        Returns:
            List of audit log entries
        """
        try:
            query = text("""
                SELECT
                    id, action, entity_type, entity_id, user_id, user_ip,
                    old_values, new_values, metadata, created_at
                FROM audit_log
                WHERE user_id = :user_id
                ORDER BY created_at DESC
                LIMIT :limit
            """)

            result = await db.execute(
                query,
                {"user_id": str(user_id), "limit": limit},
            )
            rows = result.fetchall()

            return [dict(row._mapping) for row in rows]

        except Exception as e:
            logger.error(f"Failed to get user activity: {e}")
            raise


# Singleton instance
audit_service = AuditService()
