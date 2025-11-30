"""Pytest fixtures for Ad Creative tests."""

import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def mock_mcp_client():
    """Create a mock MCP client."""
    client = AsyncMock()
    client.call_tool = AsyncMock()
    client.close = AsyncMock()
    return client


@pytest.fixture
def mock_gemini_client():
    """Create a mock Gemini client."""
    client = AsyncMock()
    return client


@pytest.fixture
def mock_redis_client():
    """Create a mock Redis client."""
    client = AsyncMock()
    client.get = AsyncMock(return_value=None)
    client.setex = AsyncMock(return_value=True)
    client.delete = AsyncMock(return_value=1)
    return client


@pytest.fixture
def sample_product_info():
    """Sample product info for testing."""
    return {
        "title": "Test Product",
        "price": 29.99,
        "currency": "USD",
        "images": ["https://example.com/image1.jpg"],
        "description": "A great test product",
        "selling_points": ["High quality", "Fast shipping", "Great value"],
        "source": "shopify",
    }


@pytest.fixture
def sample_creative():
    """Sample creative data for testing."""
    return {
        "creative_id": "creative_123",
        "user_id": "user_456",
        "url": "https://cdn.example.com/creative.png",
        "thumbnail_url": "https://cdn.example.com/creative_thumb.png",
        "aspect_ratio": "9:16",
        "platform": "tiktok",
        "score": 85.5,
        "score_dimensions": {
            "visual_impact": {"score": 90, "analysis": "Great visual impact"},
            "composition": {"score": 85, "analysis": "Good composition"},
            "color_harmony": {"score": 80, "analysis": "Nice colors"},
            "text_clarity": {"score": 87, "analysis": "Clear text"},
        },
        "created_at": "2024-01-15T10:30:00Z",
        "tags": ["product", "ad"],
    }


@pytest.fixture
def sample_competitor_analysis():
    """Sample competitor analysis for testing."""
    return {
        "composition": "Rule of thirds with product centered",
        "color_scheme": "Vibrant with blue and orange contrast",
        "selling_points": ["Free shipping", "30-day returns", "Best price"],
        "copy_structure": "Hook + benefit + CTA",
        "recommendations": [
            "Use similar color contrast",
            "Include social proof",
        ],
    }
