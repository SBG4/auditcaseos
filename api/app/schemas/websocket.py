"""Pydantic schemas for WebSocket messages."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict


class WebSocketMessageType(str, Enum):
    """Types of WebSocket messages."""

    # Server -> Client
    CONNECTED = "connected"
    PRESENCE = "presence"
    CASE_UPDATED = "case_updated"
    EVIDENCE_ADDED = "evidence_added"
    EVIDENCE_DELETED = "evidence_deleted"
    FINDING_ADDED = "finding_added"
    FINDING_UPDATED = "finding_updated"
    FINDING_DELETED = "finding_deleted"
    TIMELINE_ADDED = "timeline_added"
    COMMENT_ADDED = "comment_added"
    STATUS_CHANGED = "status_changed"
    PING = "ping"
    PONG = "pong"
    ERROR = "error"

    # Client -> Server
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    HEARTBEAT = "heartbeat"


class ViewerInfo(BaseModel):
    """Information about a user viewing a case."""

    model_config = ConfigDict(from_attributes=True)

    user_id: str
    email: str
    name: str
    connected_at: str


class PresenceMessage(BaseModel):
    """Presence update message."""

    model_config = ConfigDict(from_attributes=True)

    type: str = WebSocketMessageType.PRESENCE
    case_id: str
    viewers: list[ViewerInfo]
    timestamp: str


class CaseUpdateMessage(BaseModel):
    """Case update notification message."""

    model_config = ConfigDict(from_attributes=True)

    type: str
    case_id: str
    data: dict[str, Any]
    timestamp: str
    triggered_by: str | None = None


class ConnectedMessage(BaseModel):
    """Connection confirmation message."""

    model_config = ConfigDict(from_attributes=True)

    type: str = WebSocketMessageType.CONNECTED
    case_id: str
    user_id: str
    message: str = "Successfully connected"
    timestamp: str


class ErrorMessage(BaseModel):
    """Error message."""

    model_config = ConfigDict(from_attributes=True)

    type: str = WebSocketMessageType.ERROR
    error: str
    code: str | None = None
    timestamp: str


class ClientMessage(BaseModel):
    """Message from client to server."""

    model_config = ConfigDict(from_attributes=True)

    type: WebSocketMessageType
    case_id: str | None = None
    data: dict[str, Any] | None = None


class WebSocketStats(BaseModel):
    """WebSocket connection statistics."""

    model_config = ConfigDict(from_attributes=True)

    total_connections: int
    cases_with_viewers: int
    unique_users: int


class HealthResponse(BaseModel):
    """WebSocket health check response."""

    model_config = ConfigDict(from_attributes=True)

    status: str
    total_connections: int
    active_cases: int
