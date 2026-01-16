"""WebSocket router for real-time updates."""

import json
import logging
from datetime import datetime

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.schemas.websocket import (
    HealthResponse,
    WebSocketMessageType,
)
from app.services.websocket_service import connection_manager
from app.utils.security import decode_access_token

logger = logging.getLogger(__name__)

router = APIRouter()


async def get_user_from_token(token: str) -> dict | None:
    """
    Validate token and extract user information.

    Args:
        token: JWT token string

    Returns:
        User info dict or None if invalid
    """
    token_data = decode_access_token(token)
    if not token_data or not token_data.user_id:
        return None
    return {
        "user_id": token_data.user_id,
        "email": token_data.email,
        "role": token_data.role,
    }


@router.websocket("/cases/{case_id}")
async def websocket_case_endpoint(
    websocket: WebSocket,
    case_id: str,
    token: str = Query(..., description="JWT authentication token"),
):
    """
    WebSocket endpoint for real-time case updates.

    Connect to receive live updates for a specific case including:
    - Case data changes
    - Evidence additions/deletions
    - Finding updates
    - Timeline events
    - Presence information (who else is viewing)

    Authentication is done via the 'token' query parameter since
    WebSocket connections cannot use Authorization headers.

    Example connection URL:
    ws://localhost:18000/api/v1/ws/cases/FIN-USB-0001?token=<jwt_token>
    """
    # Authenticate user
    user = await get_user_from_token(token)
    if not user:
        await websocket.close(code=4001, reason="Invalid or expired token")
        return

    user_id = user["user_id"]
    user_email = user["email"]

    # Connect to the case room
    connected = await connection_manager.connect(
        websocket=websocket,
        case_id=case_id,
        user_id=user_id,
        user_email=user_email,
        user_name=user_email.split("@")[0],
    )

    if not connected:
        return

    # Send connection confirmation
    await websocket.send_json({
        "type": WebSocketMessageType.CONNECTED,
        "case_id": case_id,
        "user_id": user_id,
        "message": f"Connected to case {case_id}",
        "timestamp": datetime.utcnow().isoformat(),
    })

    # Send current presence
    viewers = await connection_manager.get_case_presence(case_id)
    await websocket.send_json({
        "type": WebSocketMessageType.PRESENCE,
        "case_id": case_id,
        "viewers": viewers,
        "timestamp": datetime.utcnow().isoformat(),
    })

    try:
        # Main message loop
        while True:
            try:
                # Receive message from client
                data = await websocket.receive_text()
                message = json.loads(data)
                msg_type = message.get("type")

                if msg_type == WebSocketMessageType.HEARTBEAT:
                    # Respond to heartbeat
                    await websocket.send_json({
                        "type": WebSocketMessageType.PONG,
                        "timestamp": datetime.utcnow().isoformat(),
                    })

                elif msg_type == WebSocketMessageType.SUBSCRIBE:
                    # Client wants to subscribe to a different case
                    new_case_id = message.get("case_id")
                    if new_case_id and new_case_id != case_id:
                        # Would need to disconnect and reconnect
                        await websocket.send_json({
                            "type": WebSocketMessageType.ERROR,
                            "error": "To subscribe to a different case, please open a new connection",
                            "timestamp": datetime.utcnow().isoformat(),
                        })

                else:
                    logger.debug(f"Unknown message type from client: {msg_type}")

            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": WebSocketMessageType.ERROR,
                    "error": "Invalid JSON message",
                    "timestamp": datetime.utcnow().isoformat(),
                })

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: user={user_email}, case={case_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await connection_manager.disconnect(websocket)


@router.get("/health", response_model=HealthResponse, summary="WebSocket health check")
async def websocket_health():
    """Check WebSocket service health and get connection statistics."""
    total = await connection_manager.get_connection_count()

    # Count active cases
    async with connection_manager._lock:
        active_cases = len(connection_manager._connections)

    return HealthResponse(
        status="healthy",
        total_connections=total,
        active_cases=active_cases,
    )


@router.get("/presence/{case_id}", summary="Get case viewers")
async def get_case_viewers(case_id: str):
    """
    Get list of users currently viewing a specific case.

    This endpoint doesn't require WebSocket connection - useful for
    checking presence without establishing a connection.
    """
    viewers = await connection_manager.get_case_presence(case_id)
    return {
        "case_id": case_id,
        "viewers": viewers,
        "viewer_count": len(viewers),
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.post("/broadcast/{case_id}", summary="Broadcast message to case viewers")
async def broadcast_to_case(
    case_id: str,
    message_type: str = Query(..., description="Message type"),
    data: dict = None,
):
    """
    Broadcast a message to all viewers of a case.

    This is an internal endpoint used by other services to push updates.
    In production, this should be protected or called internally only.
    """
    sent_count = await connection_manager.send_case_update(
        case_id=case_id,
        update_type=message_type,
        data=data or {},
    )
    return {
        "success": True,
        "sent_to": sent_count,
        "case_id": case_id,
        "message_type": message_type,
    }
