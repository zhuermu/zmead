"""
Property-based tests for budget increase recommendations.

**Feature: ad-performance, Property 10: High-performing entity budget increase**
**Validates: Requirements 5.3**
"""

import pytest
from hypothesis import given, settings, strategies as st

from app.modules.ad_performance.analyzers.recommendation_engine import RecommendationEngine


@given(
    roas=st.floats(min_value=3.0, max_value=10.0),  # Above high threshold (2.0 * 1.5 = 3.0)
    spend=st.floats(min_value=1.0, max_value=10000.0),
    conversions=st.integers(min_value=1, max_value=100)
)
@settings(max_examples=100)
@pytest.mark.asyncio
async def test_property_10_high_performing_entity_budget_increase(
    roas: float,
    spend: float,
    conversions: int
):
    """
    **Feature: ad-performance, Property 10: High-performing entity budget increase**
    
    For any ROAS above high threshold, generate_recommendations should generate
    action="increase_budget" recommendation.
    
    **Validates: Requirements 5.3**
    """
    # Arrange
    engine = RecommendationEngine()
    
    # Create metrics data with high-performing adset
    metrics_data = {
        "adsets": [
            {
                "entity_id": "adset_456",
                "name": "High Performer",
                "roas": roas,
                "spend": spend,
                "conversions": conversions,
                "revenue": roas * spend
            }
        ],
        "ads": []
    }
    
    constraints = {
        "min_roas_threshold": 2.0  # High threshold will be 2.0 * 1.5 = 3.0
    }
    
    # Act
    recommendations = await engine.generate(
        metrics_data=metrics_data,
        optimization_goal="maximize_roas",
        constraints=constraints
    )
    
    # Assert - should have at least one increase_budget recommendation
    budget_recommendations = [
        r for r in recommendations
        if r.action == "increase_budget"
    ]
    
    assert len(budget_recommendations) > 0, (
        f"Expected increase_budget recommendation for ROAS {roas:.2f} above threshold 3.0"
    )
    
    # Verify the budget increase recommendation has correct structure
    budget_rec = budget_recommendations[0]
    assert budget_rec.priority in ["high", "medium", "low"]
    assert budget_rec.target.type == "adset"
    assert budget_rec.target.id == "adset_456"
    assert budget_rec.target.name == "High Performer"
    assert "ROAS" in budget_rec.reason or "performance" in budget_rec.reason.lower()
    assert budget_rec.expected_impact.spend_increase is not None
    assert budget_rec.expected_impact.revenue_increase is not None
    assert budget_rec.expected_impact.spend_increase > 0
    assert budget_rec.expected_impact.revenue_increase > 0
    assert 0.0 <= budget_rec.confidence <= 1.0


@pytest.mark.asyncio
async def test_low_roas_does_not_generate_budget_increase():
    """
    Test that low ROAS entities do not generate budget increase recommendations.
    """
    # Arrange
    engine = RecommendationEngine()
    
    metrics_data = {
        "adsets": [
            {
                "entity_id": "adset_123",
                "name": "Low Performer",
                "roas": 1.5,  # Below high threshold
                "spend": 500.0,
                "conversions": 10,
                "revenue": 750.0
            }
        ],
        "ads": []
    }
    
    constraints = {
        "min_roas_threshold": 2.0  # High threshold = 3.0
    }
    
    # Act
    recommendations = await engine.generate(
        metrics_data=metrics_data,
        optimization_goal="maximize_roas",
        constraints=constraints
    )
    
    # Assert - should NOT have budget increase recommendations
    budget_recommendations = [
        r for r in recommendations
        if r.action == "increase_budget"
    ]
    
    assert len(budget_recommendations) == 0, (
        "Low ROAS entity should not generate budget increase recommendation"
    )


@pytest.mark.asyncio
async def test_identify_high_performing_filters_correctly():
    """
    Test that identify_high_performing correctly filters entities.
    """
    # Arrange
    engine = RecommendationEngine()
    
    entities = [
        {"entity_id": "1", "name": "Low", "roas": 1.0, "spend": 100},
        {"entity_id": "2", "name": "Medium", "roas": 2.5, "spend": 200},
        {"entity_id": "3", "name": "High 1", "roas": 3.5, "spend": 300},
        {"entity_id": "4", "name": "High 2", "roas": 5.0, "spend": 400},
    ]
    
    threshold = 3.0
    
    # Act
    high_performing = await engine.identify_high_performing(entities, threshold)
    
    # Assert
    assert len(high_performing) == 2
    assert all(e["roas"] >= threshold for e in high_performing)
    assert high_performing[0]["entity_id"] in ["3", "4"]
    assert high_performing[1]["entity_id"] in ["3", "4"]


@pytest.mark.asyncio
async def test_expected_impact_calculation():
    """
    Test that expected impact is calculated correctly for budget increase.
    """
    # Arrange
    engine = RecommendationEngine()
    
    spend = 1000.0
    roas = 4.0
    
    metrics_data = {
        "adsets": [
            {
                "entity_id": "adset_789",
                "name": "Test Adset",
                "roas": roas,
                "spend": spend,
                "conversions": 50,
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
    
    # Assert
    budget_rec = next(r for r in recommendations if r.action == "increase_budget")
    
    # Expected: 20% increase in spend
    expected_spend_increase = spend * 0.2
    expected_revenue_increase = expected_spend_increase * roas
    
    assert abs(budget_rec.expected_impact.spend_increase - expected_spend_increase) < 0.01
    assert abs(budget_rec.expected_impact.revenue_increase - expected_revenue_increase) < 0.01
