"""WebSocket service for real-time updates and presence tracking."""

import asyncio
import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import WebSocket
from starlette.websockets import WebSocketState

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for real-time updates."""

    def __init__(self):
        """Initialize connection manager."""
        # Active connections: {case_id: {user_id: [websocket, ...]}}
        self._connections: dict[str, dict[str, list[WebSocket]]] = {}
        # User metadata: {websocket_id: {user_id, user_email, case_id, connected_at}}
        self._metadata: dict[int, dict[str, Any]] = {}
        # Presence tracking: {case_id: {user_id: {email, name, connected_at}}}
        self._presence: dict[str, dict[str, dict[str, Any]]] = {}
        # Global user connections: {user_id: [websocket, ...]} (for notifications)
        self._user_connections: dict[str, list[WebSocket]] = {}
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()

    async def connect(
        self,
        websocket: WebSocket,
        case_id: str,
        user_id: str,
        user_email: str,
        user_name: str | None = None,
    ) -> bool:
        """
        Register a new WebSocket connection.

        Args:
            websocket: The WebSocket connection
            case_id: The case being viewed
            user_id: The authenticated user's ID
            user_email: The user's email
            user_name: Optional user display name

        Returns:
            True if connection was successful
        """
        try:
            await websocket.accept()

            async with self._lock:
                # Initialize case dict if needed
                if case_id not in self._connections:
                    self._connections[case_id] = {}
                    self._presence[case_id] = {}

                # Initialize user's connection list if needed
                if user_id not in self._connections[case_id]:
                    self._connections[case_id][user_id] = []

                # Add connection
                self._connections[case_id][user_id].append(websocket)

                # Store metadata
                ws_id = id(websocket)
                self._metadata[ws_id] = {
                    "user_id": user_id,
                    "user_email": user_email,
                    "user_name": user_name or user_email.split("@")[0],
                    "case_id": case_id,
                    "connected_at": datetime.utcnow().isoformat(),
                }

                # Update presence
                self._presence[case_id][user_id] = {
                    "email": user_email,
                    "name": user_name or user_email.split("@")[0],
                    "connected_at": datetime.utcnow().isoformat(),
                }

                # Track global user connection (for notifications)
                if user_id not in self._user_connections:
                    self._user_connections[user_id] = []
                self._user_connections[user_id].append(websocket)

            logger.info(f"WebSocket connected: user={user_email}, case={case_id}")

            # Broadcast presence update to other viewers
            await self.broadcast_presence_update(case_id, user_id)

            return True

        except Exception as e:
            logger.error(f"Failed to accept WebSocket connection: {e}")
            return False

    async def disconnect(self, websocket: WebSocket) -> None:
        """
        Remove a WebSocket connection.

        Args:
            websocket: The WebSocket to disconnect
        """
        ws_id = id(websocket)

        async with self._lock:
            metadata = self._metadata.pop(ws_id, None)
            if not metadata:
                return

            case_id = metadata["case_id"]
            user_id = metadata["user_id"]

            # Remove from connections
            if case_id in self._connections:
                if user_id in self._connections[case_id]:
                    try:
                        self._connections[case_id][user_id].remove(websocket)
                    except ValueError:
                        pass

                    # If user has no more connections to this case, remove from presence
                    if not self._connections[case_id][user_id]:
                        del self._connections[case_id][user_id]
                        if case_id in self._presence and user_id in self._presence[case_id]:
                            del self._presence[case_id][user_id]

                # Clean up empty case dicts
                if not self._connections[case_id]:
                    del self._connections[case_id]
                if case_id in self._presence and not self._presence[case_id]:
                    del self._presence[case_id]

                # Remove from global user connections
                if user_id in self._user_connections:
                    try:
                        self._user_connections[user_id].remove(websocket)
                    except ValueError:
                        pass
                    if not self._user_connections[user_id]:
                        del self._user_connections[user_id]

        logger.info(f"WebSocket disconnected: user={metadata.get('user_email')}, case={case_id}")

        # Broadcast presence update
        await self.broadcast_presence_update(case_id, user_id)

    async def broadcast_to_case(
        self,
        case_id: str,
        message: dict[str, Any],
        exclude_user: str | None = None,
    ) -> int:
        """
        Broadcast a message to all users viewing a case.

        Args:
            case_id: The case ID to broadcast to
            message: The message to send
            exclude_user: Optional user ID to exclude from broadcast

        Returns:
            Number of connections that received the message
        """
        sent_count = 0
        dead_connections: list[tuple[str, WebSocket]] = []

        async with self._lock:
            if case_id not in self._connections:
                return 0

            for user_id, connections in self._connections[case_id].items():
                if exclude_user and user_id == exclude_user:
                    continue

                for websocket in connections:
                    try:
                        if websocket.client_state == WebSocketState.CONNECTED:
                            await websocket.send_json(message)
                            sent_count += 1
                        else:
                            dead_connections.append((user_id, websocket))
                    except Exception as e:
                        logger.warning(f"Failed to send WebSocket message: {e}")
                        dead_connections.append((user_id, websocket))

        # Clean up dead connections outside the lock
        for user_id, ws in dead_connections:
            await self.disconnect(ws)

        return sent_count

    async def broadcast_presence_update(self, case_id: str, trigger_user_id: str) -> None:
        """
        Broadcast presence update to all viewers of a case.

        Args:
            case_id: The case ID
            trigger_user_id: The user who triggered the update
        """
        presence_list = await self.get_case_presence(case_id)
        message = {
            "type": "presence",
            "case_id": case_id,
            "viewers": presence_list,
            "timestamp": datetime.utcnow().isoformat(),
        }
        await self.broadcast_to_case(case_id, message)

    async def send_case_update(
        self,
        case_id: str,
        update_type: str,
        data: dict[str, Any],
        triggered_by: str | None = None,
    ) -> int:
        """
        Send a case update notification to all viewers.

        Args:
            case_id: The case that was updated
            update_type: Type of update (case_updated, evidence_added, finding_added, etc.)
            data: The update data
            triggered_by: User ID who triggered the update (will be excluded)

        Returns:
            Number of connections notified
        """
        message = {
            "type": update_type,
            "case_id": case_id,
            "data": data,
            "timestamp": datetime.utcnow().isoformat(),
        }
        return await self.broadcast_to_case(case_id, message, exclude_user=triggered_by)

    async def get_case_presence(self, case_id: str) -> list[dict[str, Any]]:
        """
        Get list of users currently viewing a case.

        Args:
            case_id: The case ID

        Returns:
            List of viewer information
        """
        async with self._lock:
            if case_id not in self._presence:
                return []
            return [
                {"user_id": user_id, **info}
                for user_id, info in self._presence[case_id].items()
            ]

    async def get_connection_count(self, case_id: str | None = None) -> int:
        """
        Get total number of active connections.

        Args:
            case_id: Optional case ID to filter by

        Returns:
            Number of active connections
        """
        async with self._lock:
            if case_id:
                if case_id not in self._connections:
                    return 0
                return sum(
                    len(conns) for conns in self._connections[case_id].values()
                )
            return sum(
                len(conns)
                for case_conns in self._connections.values()
                for conns in case_conns.values()
            )

    async def send_to_user(
        self,
        user_id: str,
        message: dict[str, Any],
        case_id: str | None = None,
    ) -> int:
        """
        Send a message to a specific user.

        Args:
            user_id: The user to send to
            message: The message to send
            case_id: Optional case ID to limit scope

        Returns:
            Number of connections that received the message
        """
        sent_count = 0
        dead_connections: list[tuple[str, str, WebSocket]] = []

        async with self._lock:
            cases_to_check = [case_id] if case_id else list(self._connections.keys())

            for cid in cases_to_check:
                if cid not in self._connections:
                    continue
                if user_id not in self._connections[cid]:
                    continue

                for websocket in self._connections[cid][user_id]:
                    try:
                        if websocket.client_state == WebSocketState.CONNECTED:
                            await websocket.send_json(message)
                            sent_count += 1
                        else:
                            dead_connections.append((cid, user_id, websocket))
                    except Exception as e:
                        logger.warning(f"Failed to send to user {user_id}: {e}")
                        dead_connections.append((cid, user_id, websocket))

        # Clean up dead connections
        for _, _, ws in dead_connections:
            await self.disconnect(ws)

        return sent_count

    async def send_notification(
        self,
        user_id: str,
        notification_data: dict[str, Any],
    ) -> int:
        """
        Send a notification to a specific user across all their connections.

        Args:
            user_id: The user to notify
            notification_data: The notification data

        Returns:
            Number of connections that received the notification
        """
        message = {
            "type": "notification",
            "data": notification_data,
            "timestamp": datetime.utcnow().isoformat(),
        }

        sent_count = 0
        dead_connections: list[WebSocket] = []

        async with self._lock:
            if user_id not in self._user_connections:
                return 0

            for websocket in self._user_connections[user_id]:
                try:
                    if websocket.client_state == WebSocketState.CONNECTED:
                        await websocket.send_json(message)
                        sent_count += 1
                    else:
                        dead_connections.append(websocket)
                except Exception as e:
                    logger.warning(f"Failed to send notification to user {user_id}: {e}")
                    dead_connections.append(websocket)

        # Clean up dead connections
        for ws in dead_connections:
            await self.disconnect(ws)

        return sent_count

    async def send_notification_to_many(
        self,
        user_ids: list[str],
        notification_data: dict[str, Any],
    ) -> dict[str, int]:
        """
        Send a notification to multiple users.

        Args:
            user_ids: List of user IDs to notify
            notification_data: The notification data

        Returns:
            Dict with sent and failed counts
        """
        sent = 0
        failed = 0

        for user_id in user_ids:
            count = await self.send_notification(user_id, notification_data)
            if count > 0:
                sent += 1
            else:
                failed += 1

        return {"sent": sent, "failed": failed, "total": len(user_ids)}

    async def broadcast_notification(
        self,
        notification_data: dict[str, Any],
        priority: str | None = None,
    ) -> int:
        """
        Broadcast a notification to all connected users.

        Args:
            notification_data: The notification data
            priority: Optional priority filter (only send to users with matching priority level)

        Returns:
            Number of users notified
        """
        message = {
            "type": "notification",
            "data": notification_data,
            "timestamp": datetime.utcnow().isoformat(),
        }

        sent_count = 0
        dead_connections: list[WebSocket] = []

        async with self._lock:
            for user_id, connections in self._user_connections.items():
                user_sent = False
                for websocket in connections:
                    try:
                        if websocket.client_state == WebSocketState.CONNECTED:
                            await websocket.send_json(message)
                            if not user_sent:
                                sent_count += 1
                                user_sent = True
                        else:
                            dead_connections.append(websocket)
                    except Exception as e:
                        logger.warning(f"Failed to broadcast notification: {e}")
                        dead_connections.append(websocket)

        # Clean up dead connections
        for ws in dead_connections:
            await self.disconnect(ws)

        return sent_count

    async def get_connected_user_ids(self) -> list[str]:
        """
        Get list of all connected user IDs.

        Returns:
            List of user IDs with active connections
        """
        async with self._lock:
            return list(self._user_connections.keys())

    async def ping_all(self) -> dict[str, int]:
        """
        Send ping to all connections to check health.

        Returns:
            Dict with total and failed counts
        """
        total = 0
        failed = 0
        dead_connections: list[WebSocket] = []

        ping_message = {
            "type": "ping",
            "timestamp": datetime.utcnow().isoformat(),
        }

        async with self._lock:
            for case_conns in self._connections.values():
                for connections in case_conns.values():
                    for websocket in connections:
                        total += 1
                        try:
                            if websocket.client_state == WebSocketState.CONNECTED:
                                await websocket.send_json(ping_message)
                            else:
                                failed += 1
                                dead_connections.append(websocket)
                        except Exception:
                            failed += 1
                            dead_connections.append(websocket)

        # Clean up dead connections
        for ws in dead_connections:
            await self.disconnect(ws)

        return {"total": total, "failed": failed, "active": total - failed}


# Singleton instance
connection_manager = ConnectionManager()
