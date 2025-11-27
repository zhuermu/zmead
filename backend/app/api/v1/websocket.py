"""WebSocket endpoint for real-time chat communication."""

import asyncio
import json
import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from fastapi.exceptions import WebSocketException

from app.core.redis import get_redis
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()


class ConnectionManager:
    """Manages active WebSocket connections."""

    def __init__(self):
        """Initialize connection manager."""
        self.active_connections: dict[str, WebSocket] = {}
        self.user_sessions: dict[str, str] = {}  # user_id -> session_id

    async def connect(self, websocket: WebSocket, user_id: str, session_id: str):
        """Accept and store a new WebSocket connection."""
        await websocket.accept()
        self.active_connections[session_id] = websocket
        self.user_sessions[user_id] = session_id
        logger.info(f"WebSocket connected: user_id={user_id}, session_id={session_id}")

        # Store connection info in Redis for distributed systems
        redis = await get_redis()
        await redis.setex(
            f"ws:session:{session_id}",
            3600,  # 1 hour TTL
            json.dumps({
                "user_id": user_id,
                "connected_at": datetime.now(UTC).isoformat(),
            })
        )

    async def disconnect(self, session_id: str):
        """Remove a WebSocket connection."""
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            logger.info(
                f"WebSocket disconnected: session_id={session_id}, "
                f"active_connections={len(self.active_connections)}"
            )

            # Remove from Redis
            redis = await get_redis()
            await redis.delete(f"ws:session:{session_id}")
            await redis.delete(f"ws:heartbeat:{session_id}")
            await redis.delete(f"ws:pong:{session_id}")

            # Clean up user_sessions mapping
            for user_id, sid in list(self.user_sessions.items()):
                if sid == session_id:
                    del self.user_sessions[user_id]
                    break

            # Log connection metrics
            await self._log_connection_metrics()

    async def send_message(self, session_id: str, message: dict[str, Any]):
        """Send a message to a specific session."""
        if session_id in self.active_connections:
            websocket = self.active_connections[session_id]
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error sending message to {session_id}: {e}")
                await self.disconnect(session_id)

    async def send_to_user(self, user_id: str, message: dict[str, Any]):
        """Send a message to a user's active session."""
        session_id = self.user_sessions.get(user_id)
        if session_id:
            await self.send_message(session_id, message)

    def get_active_connections_count(self) -> int:
        """Get the number of active connections."""
        return len(self.active_connections)

    async def broadcast(self, message: dict[str, Any]):
        """Broadcast a message to all connected clients."""
        disconnected = []
        for session_id, websocket in self.active_connections.items():
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to {session_id}: {e}")
                disconnected.append(session_id)

        # Clean up disconnected sessions
        for session_id in disconnected:
            await self.disconnect(session_id)

    async def _log_connection_metrics(self):
        """Log connection metrics to Redis for monitoring."""
        redis = await get_redis()
        metrics = {
            "active_connections": len(self.active_connections),
            "active_users": len(self.user_sessions),
            "timestamp": datetime.now(UTC).isoformat(),
        }
        await redis.setex(
            "ws:metrics:current",
            300,  # 5 minutes TTL
            json.dumps(metrics)
        )
        logger.info(f"WebSocket metrics: {metrics}")


# Global connection manager instance
manager = ConnectionManager()


@router.websocket("/ws/chat")
async def websocket_chat_endpoint(
    websocket: WebSocket,
    token: str | None = None,
):
    """
    WebSocket endpoint for real-time chat communication.
    
    Authentication is done via query parameter: /ws/chat?token=<jwt_token>
    
    Requirements: 12.1.1
    """
    # Authenticate user
    try:
        # Get user from token
        if not token:
            raise WebSocketException(
                code=status.WS_1008_POLICY_VIOLATION,
                reason="Missing authentication token"
            )
        
        # Validate token and get user
        from app.core.security import decode_token
        from app.core.database import get_db
        from app.services.auth import AuthService
        
        payload = decode_token(token)
        if not payload:
            raise WebSocketException(
                code=status.WS_1008_POLICY_VIOLATION,
                reason="Invalid or expired token"
            )
        
        if payload.get("type") != "access":
            raise WebSocketException(
                code=status.WS_1008_POLICY_VIOLATION,
                reason="Invalid token type"
            )
        
        user_id = payload.get("sub")
        if not user_id:
            raise WebSocketException(
                code=status.WS_1008_POLICY_VIOLATION,
                reason="Invalid token"
            )
        
        # Get database session and user
        async for db in get_db():
            auth_service = AuthService(db)
            user = await auth_service.get_user_by_id(int(user_id))
            if not user:
                raise WebSocketException(
                    code=status.WS_1008_POLICY_VIOLATION,
                    reason="User not found"
                )
            break
        
    except Exception as e:
        logger.error(f"WebSocket authentication failed: {e}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication failed")
        return

    # Generate session ID
    import uuid
    session_id = str(uuid.uuid4())

    # Connect
    await manager.connect(websocket, str(user.id), session_id)

    try:
        # Send connection confirmation
        await websocket.send_json({
            "type": "connection_established",
            "session_id": session_id,
            "user_id": str(user.id),
            "timestamp": datetime.now(UTC).isoformat(),
        })

        # Start heartbeat task
        heartbeat_task = asyncio.create_task(
            send_heartbeat(websocket, session_id)
        )

        # Message handling loop
        while True:
            try:
                # Receive message from client
                data = await websocket.receive_text()
                message = json.loads(data)

                # Log received message
                logger.info(f"Received message from {session_id}: {message.get('type')}")

                # Handle different message types
                message_type = message.get("type")

                if message_type == "pong":
                    # Client responded to ping
                    logger.debug(f"Received pong from {session_id}")
                    await update_pong_time(session_id)
                    continue

                elif message_type == "user_message":
                    # Forward to message handler (will be implemented in 25.2)
                    await handle_user_message(websocket, user, session_id, message)

                else:
                    logger.warning(f"Unknown message type: {message_type}")
                    await websocket.send_json({
                        "type": "error",
                        "error": {
                            "code": "UNKNOWN_MESSAGE_TYPE",
                            "message": f"Unknown message type: {message_type}",
                        },
                        "timestamp": datetime.now(UTC).isoformat(),
                    })

            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON from {session_id}: {e}")
                await websocket.send_json({
                    "type": "error",
                    "error": {
                        "code": "INVALID_JSON",
                        "message": "Invalid JSON format",
                    },
                    "timestamp": datetime.now(UTC).isoformat(),
                })

    except WebSocketDisconnect:
        logger.info(f"Client disconnected: {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error for {session_id}: {e}")
    finally:
        # Cancel heartbeat task
        if 'heartbeat_task' in locals():
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                pass

        # Disconnect
        await manager.disconnect(session_id)


async def send_heartbeat(websocket: WebSocket, session_id: str):
    """
    Send periodic ping messages to keep connection alive.
    Detect disconnection if no pong received within 60 seconds.
    
    Requirements: 12.1.2
    """
    last_pong_time = datetime.now(UTC)
    redis = await get_redis()
    
    try:
        while True:
            await asyncio.sleep(30)  # Send ping every 30 seconds
            
            # Check if we received pong in the last 60 seconds
            current_time = datetime.now(UTC)
            time_since_pong = (current_time - last_pong_time).total_seconds()
            
            if time_since_pong > 60:
                logger.warning(
                    f"No pong received from {session_id} for {time_since_pong:.1f}s. "
                    "Closing connection."
                )
                # Connection is stale, close it
                await websocket.close(code=status.WS_1001_GOING_AWAY, reason="Heartbeat timeout")
                break
            
            try:
                # Send ping
                await websocket.send_json({
                    "type": "ping",
                    "timestamp": current_time.isoformat(),
                })
                logger.debug(f"Sent ping to {session_id}")
                
                # Update last ping time in Redis for monitoring
                await redis.setex(
                    f"ws:heartbeat:{session_id}",
                    120,  # 2 minutes TTL
                    json.dumps({
                        "last_ping": current_time.isoformat(),
                        "last_pong": last_pong_time.isoformat(),
                    })
                )
                
            except Exception as e:
                logger.error(f"Failed to send ping to {session_id}: {e}")
                break
                
    except asyncio.CancelledError:
        logger.debug(f"Heartbeat task cancelled for {session_id}")
        # Clean up heartbeat data
        await redis.delete(f"ws:heartbeat:{session_id}")


async def update_pong_time(session_id: str):
    """Update the last pong time for a session."""
    # This will be called when we receive a pong message
    # Store in Redis for distributed systems
    redis = await get_redis()
    await redis.setex(
        f"ws:pong:{session_id}",
        120,  # 2 minutes TTL
        datetime.now(UTC).isoformat()
    )


async def handle_user_message(
    websocket: WebSocket,
    user: User,
    session_id: str,
    message: dict[str, Any],
):
    """
    Handle user message by forwarding to AI Orchestrator and streaming response.
    
    Requirements: 4.1.4, 4.2.2
    """
    import httpx
    from app.core.config import settings

    # Validate message format
    content = message.get("content")
    if not content:
        await websocket.send_json({
            "type": "error",
            "error": {
                "code": "INVALID_MESSAGE",
                "message": "Message content is required",
            },
            "timestamp": datetime.now(UTC).isoformat(),
        })
        return

    message_id = message.get("message_id", str(datetime.now(UTC).timestamp()))

    # Acknowledge receipt
    await websocket.send_json({
        "type": "message_received",
        "message_id": message_id,
        "timestamp": datetime.now(UTC).isoformat(),
    })

    try:
        # Forward to AI Orchestrator
        async with httpx.AsyncClient(timeout=settings.ai_orchestrator_timeout) as client:
            # Prepare request payload
            payload = {
                "messages": [
                    {
                        "role": "user",
                        "content": content,
                    }
                ],
                "user_id": str(user.id),
                "session_id": session_id,
            }

            # Send request to AI Orchestrator
            async with client.stream(
                "POST",
                f"{settings.ai_orchestrator_url}/chat",
                json=payload,
                headers={
                    "Content-Type": "application/json",
                },
            ) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    logger.error(f"AI Orchestrator error: {response.status_code} - {error_text}")
                    await websocket.send_json({
                        "type": "error",
                        "error": {
                            "code": "AI_ORCHESTRATOR_ERROR",
                            "message": "Failed to get response from AI",
                            "details": error_text.decode() if error_text else None,
                        },
                        "timestamp": datetime.now(UTC).isoformat(),
                    })
                    return

                # Stream response back to client
                accumulated_content = ""
                async for chunk in response.aiter_text():
                    if chunk:
                        accumulated_content += chunk
                        
                        # Send streaming chunk to client
                        await websocket.send_json({
                            "type": "agent_message_chunk",
                            "message_id": message_id,
                            "content": chunk,
                            "timestamp": datetime.now(UTC).isoformat(),
                        })

                # Send completion message
                await websocket.send_json({
                    "type": "agent_message_complete",
                    "message_id": message_id,
                    "full_content": accumulated_content,
                    "timestamp": datetime.now(UTC).isoformat(),
                })

    except httpx.TimeoutException:
        logger.error(f"AI Orchestrator timeout for session {session_id}")
        await websocket.send_json({
            "type": "error",
            "error": {
                "code": "TIMEOUT",
                "message": "Response timeout. Please try again.",
            },
            "timestamp": datetime.now(UTC).isoformat(),
        })

    except httpx.ConnectError:
        logger.error(f"Cannot connect to AI Orchestrator: {settings.ai_orchestrator_url}")
        await websocket.send_json({
            "type": "error",
            "error": {
                "code": "CONNECTION_FAILED",
                "message": "Cannot connect to AI service. Please try again later.",
            },
            "timestamp": datetime.now(UTC).isoformat(),
        })

    except Exception as e:
        logger.error(f"Error handling user message: {e}", exc_info=True)
        await websocket.send_json({
            "type": "error",
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An error occurred while processing your message",
            },
            "timestamp": datetime.now(UTC).isoformat(),
        })
