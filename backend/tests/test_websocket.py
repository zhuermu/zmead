"""Tests for WebSocket chat endpoint."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.main import app
from app.models.user import User


@pytest.fixture
def test_user():
    """Create a test user."""
    user = User(
        id=1,
        email="test@example.com",
        display_name="Test User",
        oauth_provider="google",
        oauth_id="google_123",
    )
    return user


@pytest.fixture
def mock_auth_service(test_user):
    """Mock authentication service."""
    with patch("app.api.v1.websocket.AuthService") as mock:
        mock_instance = MagicMock()
        mock_instance.get_user_by_id = AsyncMock(return_value=test_user)
        mock.return_value = mock_instance
        yield mock


@pytest.fixture
def valid_token():
    """Create a valid JWT token."""
    from app.core.security import create_access_token
    
    token = create_access_token({"sub": "1"})
    return token


def test_websocket_requires_authentication():
    """Test that WebSocket endpoint requires authentication."""
    client = TestClient(app)
    
    # Try to connect without token
    with pytest.raises(Exception):
        with client.websocket_connect("/api/v1/ws/chat"):
            pass


def test_websocket_rejects_invalid_token():
    """Test that WebSocket endpoint rejects invalid tokens."""
    client = TestClient(app)
    
    # Try to connect with invalid token
    with pytest.raises(Exception):
        with client.websocket_connect("/api/v1/ws/chat?token=invalid_token"):
            pass


@pytest.mark.asyncio
async def test_connection_manager_connect_disconnect():
    """Test ConnectionManager connect and disconnect."""
    from app.api.v1.websocket import ConnectionManager
    from unittest.mock import AsyncMock
    
    manager = ConnectionManager()
    
    # Mock WebSocket
    mock_ws = AsyncMock()
    mock_ws.accept = AsyncMock()
    
    # Mock Redis
    with patch("app.api.v1.websocket.get_redis") as mock_redis:
        mock_redis_instance = AsyncMock()
        mock_redis_instance.setex = AsyncMock()
        mock_redis_instance.delete = AsyncMock()
        mock_redis.return_value = mock_redis_instance
        
        # Test connect
        await manager.connect(mock_ws, "user_123", "session_456")
        assert "session_456" in manager.active_connections
        assert manager.user_sessions["user_123"] == "session_456"
        mock_ws.accept.assert_called_once()
        
        # Test disconnect
        await manager.disconnect("session_456")
        assert "session_456" not in manager.active_connections
        assert "user_123" not in manager.user_sessions


@pytest.mark.asyncio
async def test_connection_manager_send_message():
    """Test ConnectionManager send_message."""
    from app.api.v1.websocket import ConnectionManager
    from unittest.mock import AsyncMock
    
    manager = ConnectionManager()
    
    # Mock WebSocket
    mock_ws = AsyncMock()
    mock_ws.send_json = AsyncMock()
    
    # Add connection
    manager.active_connections["session_123"] = mock_ws
    
    # Send message
    test_message = {"type": "test", "content": "Hello"}
    await manager.send_message("session_123", test_message)
    
    mock_ws.send_json.assert_called_once_with(test_message)


@pytest.mark.asyncio
async def test_connection_manager_broadcast():
    """Test ConnectionManager broadcast."""
    from app.api.v1.websocket import ConnectionManager
    from unittest.mock import AsyncMock
    
    manager = ConnectionManager()
    
    # Mock WebSockets
    mock_ws1 = AsyncMock()
    mock_ws1.send_json = AsyncMock()
    mock_ws2 = AsyncMock()
    mock_ws2.send_json = AsyncMock()
    
    # Add connections
    manager.active_connections["session_1"] = mock_ws1
    manager.active_connections["session_2"] = mock_ws2
    
    # Mock Redis for disconnect
    with patch("app.api.v1.websocket.get_redis") as mock_redis:
        mock_redis_instance = AsyncMock()
        mock_redis_instance.delete = AsyncMock()
        mock_redis.return_value = mock_redis_instance
        
        # Broadcast message
        test_message = {"type": "broadcast", "content": "Hello everyone"}
        await manager.broadcast(test_message)
        
        mock_ws1.send_json.assert_called_once_with(test_message)
        mock_ws2.send_json.assert_called_once_with(test_message)


def test_chat_http_endpoint_requires_authentication():
    """Test that HTTP chat endpoint requires authentication."""
    client = TestClient(app)
    
    response = client.post(
        "/api/v1/chat",
        json={"messages": [{"role": "user", "content": "Hello"}]},
    )
    
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_chat_http_endpoint_validates_request():
    """Test that HTTP chat endpoint validates request format."""
    client = TestClient(app)
    
    # Create a valid token
    from app.core.security import create_access_token
    token = create_access_token({"sub": "1"})
    
    # Send invalid request (missing messages)
    response = client.post(
        "/api/v1/chat",
        json={},
        headers={"Authorization": f"Bearer {token}"},
    )
    
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
