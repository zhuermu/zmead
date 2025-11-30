"""
Test configuration for Ad Performance module.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from hypothesis import settings

# Configure Hypothesis to run 100 iterations for all property-based tests
settings.register_profile("default", max_examples=100)
settings.load_profile("default")


@pytest.fixture
def mock_mcp_client():
    """Fixture for mock MCP client"""
    client = AsyncMock()
    client.call_tool = AsyncMock(return_value={"status": "success"})
    return client


@pytest.fixture
def mock_gemini_client():
    """Fixture for mock Gemini client"""
    client = AsyncMock()
    # Mock generate_content to return an object with .text attribute
    mock_response = MagicMock()
    mock_response.text = '{"key_insights": ["Test insight"], "trends": {"roas_trend": "stable"}}'
    client.generate_content = AsyncMock(return_value=mock_response)
    client.chat_completion = AsyncMock(return_value="Mock AI response")
    return client


@pytest.fixture
def mock_redis_client():
    """Fixture for mock Redis client"""
    client = AsyncMock()
    client.get = AsyncMock(return_value=None)
    client.set = AsyncMock(return_value=True)
    return client


@pytest.fixture
def ad_performance(mock_mcp_client, mock_gemini_client, mock_redis_client):
    """Fixture for AdPerformance instance with mocked dependencies"""
    from app.modules.ad_performance import AdPerformance

    return AdPerformance(
        mcp_client=mock_mcp_client,
        gemini_client=mock_gemini_client,
        redis_client=mock_redis_client,
    )


@pytest.fixture
def sample_context():
    """Fixture for sample context"""
    return {"user_id": "test_user_123", "session_id": "test_session_456"}
