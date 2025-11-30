"""
Property-based tests for pause recommendations.

**Feature: ad-performance, Property 9: Low-performing entity pause recommendation**
**Validates: Requirements 5.2**
"""

import pytest
from hypothesis import given, settings, strategies as st

from app.modules.ad_performance.analyzers.recommendation_engine import RecommendationEngine


@given(
    roas=st.floats(min_value=0.0, max_value=1.99),  # Below threshold of 2.0
    spend=st.floats(min_value=1.0, max_value=10000.0),
    conversions=st.integers(min_value=0, max_value=100)
)
@settings(max_examples=100)
@pytest.mark.asyncio
async def test_property_9_low_performing_entity_pause_recommendation(
    roas: float,
    spend: float,
    conversions: int
):
    """
    **Feature: ad-performance, Property 9: Low-performing entity pause recommendation**
    
    For any ROAS below threshold, generate_recommendations should generate
    action="pause_adset" recommendation.
    
    **Validates: Requirements 5.2**
    """
    # Arrange
    engine = RecommendationEngine()
    
    # Create metrics data with low-performing adset
    metrics_data = {
        "adsets": [
            {
                "entity_id": "adset_123",
                "name": "Test Adset",
                "roas": roas,
                "spend": spend,
                "conversions": conversions,
                "revenue": roas * spend
            }
        ],
        "ads": []
    }
    
    constraints = {
        "min_roas_threshold": 2.0
    }
    
    # Act
    recommendations = await engine.generate(
        metrics_data=metrics_data,
        optimization_goal="maximize_roas",
        constraints=constraints
    )
    
    # Assert - should have at least one pause recommendation
    pause_recommendations = [
        r for r in recommendations
        if r.action == "pause_adset"
    ]
    
    assert len(pause_recommendations) > 0, (
        f"Expected pause recommendation for ROAS {roas:.2f} below threshold 2.0"
    )
    
    # Verify the pause recommendation has correct structure
    pause_rec = pause_recommendations[0]
    assert pause_rec.priority in ["high", "medium", "low"]
    assert pause_rec.target.type == "adset"
    assert pause_rec.target.id == "adset_123"
    assert pause_rec.target.name == "Test Adset"
    assert "ROAS" in pause_rec.reason or "underperforming" in pause_rec.reason.lower()
    assert pause_rec.expected_impact.spend_reduction is not None
    assert 0.0 <= pause_rec.confidence <= 1.0


@pytest.mark.asyncio
async def test_high_roas_does_not_generate_pause_recommendation():
    """
    Test that high ROAS entities do not generate pause recommendations.
    """
    # Arrange
    engine = RecommendationEngine()
    
    metrics_data = {
        "adsets": [
            {
                "entity_id": "adset_456",
                "name": "High Performer",
                "roas": 5.0,  # Well above threshold
                "spend": 500.0,
                "conversions": 50,
                "revenue": 2500.0
            }
        ],
        "ads": []
    }
    
    constraints = {
        "min_roas_threshold": 2.0
    }
    
    # Act
    recommendations = await engine.generate(
        metrics_data=metrics_data,
        optimization_goal="maximize_roas",
        constraints=constraints
    )
    
    # Assert - should NOT have pause recommendations
    pause_recommendations = [
        r for r in recommendations
        if r.action == "pause_adset"
    ]
    
    assert len(pause_recommendations) == 0, (
        "High ROAS entity should not generate pause recommendation"
    )


@pytest.mark.asyncio
async def test_identify_underperforming_filters_correctly():
    """
    Test that identify_underperforming correctly filters entities.
    """
    # Arrange
    engine = RecommendationEngine()
    
    entities = [
        {"entity_id": "1", "name": "Low 1", "roas": 1.0, "spend": 100},
        {"entity_id": "2", "name": "Low 2", "roas": 1.5, "spend": 200},
        {"entity_id": "3", "name": "Good", "roas": 2.5, "spend": 300},
        {"entity_id": "4", "name": "High", "roas": 4.0, "spend": 400},
    ]
    
    threshold = 2.0
    
    # Act
    underperforming = await engine.identify_underperforming(entities, threshold)
    
    # Assert
    assert len(underperforming) == 2
    assert all(e["roas"] < threshold for e in underperforming)
    assert underperforming[0]["entity_id"] in ["1", "2"]
    assert underperforming[1]["entity_id"] in ["1", "2"]
