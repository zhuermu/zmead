"""
Property-based tests for creative refresh recommendations.

**Feature: ad-performance, Property 11: Creative fatigue refresh recommendation**
**Validates: Requirements 5.4**
"""

import pytest
from hypothesis import given, settings, strategies as st
from unittest.mock import AsyncMock, MagicMock

from app.modules.ad_performance.analyzers.recommendation_engine import RecommendationEngine


@given(
    baseline_ctr=st.floats(min_value=0.01, max_value=0.10),  # 1% to 10%
    decline_factor=st.floats(min_value=0.3, max_value=0.9),  # 30% to 90% decline
    spend=st.floats(min_value=1.0, max_value=10000.0)
)
@settings(max_examples=100)
@pytest.mark.asyncio
async def test_property_11_creative_fatigue_refresh_recommendation(
    baseline_ctr: float,
    decline_factor: float,
    spend: float
):
    """
    **Feature: ad-performance, Property 11: Creative fatigue refresh recommendation**
    
    For any CTR declining by 30%+, generate_recommendations should generate
    action="refresh_creative" recommendation.
    
    **Validates: Requirements 5.4**
    """
    # Arrange
    engine = RecommendationEngine()
    
    # Calculate recent CTR with decline
    recent_ctr = baseline_ctr * (1 - decline_factor)
    
    # Mock MCP client to return historical CTR data
    mock_mcp = AsyncMock()
    
    # Create historical trend: baseline for first 3 days, then declining
    ctr_trend = [baseline_ctr] * 3 + [recent_ctr]
    
    async def mock_get_ctr_trend(*args, **kwargs):
        return ctr_trend
    
    engine._get_ctr_trend = mock_get_ctr_trend
    engine.mcp_client = mock_mcp
    
    # Create metrics data with ad showing fatigue
    metrics_data = {
        "adsets": [],
        "ads": [
            {
                "entity_id": "ad_789",
                "name": "Test Ad",
                "ctr": recent_ctr,
                "spend": spend,
                "impressions": 10000,
                "clicks": int(recent_ctr * 10000)
            }
        ]
    }
    
    # Act
    recommendations = await engine.generate(
        metrics_data=metrics_data,
        optimization_goal="maximize_roas",
        constraints={}
    )
    
    # Assert - should have at least one refresh_creative recommendation
    refresh_recommendations = [
        r for r in recommendations
        if r.action == "refresh_creative"
    ]
    
    assert len(refresh_recommendations) > 0, (
        f"Expected refresh_creative recommendation for CTR decline from "
        f"{baseline_ctr:.4f} to {recent_ctr:.4f} ({decline_factor*100:.1f}% decline)"
    )
    
    # Verify the refresh recommendation has correct structure
    refresh_rec = refresh_recommendations[0]
    assert refresh_rec.priority in ["high", "medium", "low"]
    assert refresh_rec.target.type == "ad"
    assert refresh_rec.target.id == "ad_789"
    assert refresh_rec.target.name == "Test Ad"
    assert "CTR" in refresh_rec.reason or "fatigue" in refresh_rec.reason.lower()
    assert refresh_rec.expected_impact.ctr_improvement is not None
    assert 0.0 <= refresh_rec.confidence <= 1.0


@pytest.mark.asyncio
async def test_stable_ctr_does_not_generate_refresh():
    """
    Test that stable CTR does not generate refresh recommendations.
    """
    # Arrange
    engine = RecommendationEngine()
    
    stable_ctr = 0.05
    
    # Mock MCP client
    async def mock_get_historical(*args, **kwargs):
        return [
            {"ctr": stable_ctr, "roas": 2.5, "spend": 100}
            for _ in range(7)
        ]
    
    engine._get_historical_performance = mock_get_historical
    engine.mcp_client = AsyncMock()
    
    metrics_data = {
        "adsets": [],
        "ads": [
            {
                "entity_id": "ad_456",
                "name": "Stable Ad",
                "ctr": stable_ctr,
                "spend": 500.0,
                "impressions": 10000,
                "clicks": 500
            }
        ]
    }
    
    # Act
    recommendations = await engine.generate(
        metrics_data=metrics_data,
        optimization_goal="maximize_roas",
        constraints={}
    )
    
    # Assert - should NOT have refresh recommendations
    refresh_recommendations = [
        r for r in recommendations
        if r.action == "refresh_creative"
    ]
    
    assert len(refresh_recommendations) == 0, (
        "Stable CTR should not generate refresh recommendation"
    )


@pytest.mark.asyncio
async def test_detect_creative_fatigue_identifies_declining_ctr():
    """
    Test that detect_creative_fatigue correctly identifies declining CTR.
    """
    # Arrange
    engine = RecommendationEngine()
    
    baseline_ctr = 0.08
    recent_ctr = 0.04  # 50% decline
    
    # Mock historical data
    async def mock_get_historical(*args, **kwargs):
        return [
            {"ctr": baseline_ctr, "roas": 2.5, "spend": 100},
            {"ctr": baseline_ctr, "roas": 2.5, "spend": 100},
            {"ctr": baseline_ctr, "roas": 2.5, "spend": 100},
            {"ctr": recent_ctr, "roas": 2.5, "spend": 100},
        ]
    
    engine._get_historical_performance = mock_get_historical
    engine.mcp_client = AsyncMock()
    
    entities = [
        {
            "entity_id": "ad_123",
            "name": "Fatigued Ad",
            "ctr": recent_ctr,
            "spend": 400
        }
    ]
    
    # Act
    fatigued = await engine.detect_creative_fatigue(entities, decline_threshold=0.3)
    
    # Assert
    assert len(fatigued) == 1
    assert fatigued[0]["entity_id"] == "ad_123"
    assert "ctr_decline_pct" in fatigued[0]
    assert fatigued[0]["ctr_decline_pct"] >= 30.0  # At least 30% decline


@pytest.mark.asyncio
async def test_insufficient_data_does_not_trigger_fatigue():
    """
    Test that insufficient historical data doesn't trigger fatigue detection.
    """
    # Arrange
    engine = RecommendationEngine()
    
    # Mock insufficient historical data (less than min_days_for_trend)
    async def mock_get_historical(*args, **kwargs):
        return [
            {"ctr": 0.05, "roas": 2.5, "spend": 100},
            {"ctr": 0.03, "roas": 2.5, "spend": 100},
        ]
    
    engine._get_historical_performance = mock_get_historical
    engine.mcp_client = AsyncMock()
    
    entities = [
        {
            "entity_id": "ad_new",
            "name": "New Ad",
            "ctr": 0.03,
            "spend": 200
        }
    ]
    
    # Act
    fatigued = await engine.detect_creative_fatigue(entities, decline_threshold=0.3)
    
    # Assert - should not detect fatigue with insufficient data
    assert len(fatigued) == 0
