"""
Property-based tests for recommendation data completeness.

**Feature: ad-performance, Property 12: Recommendation data completeness**
**Validates: Requirements 5.1, 5.5, 10.1, 10.2, 10.3, 10.4, 10.5**
"""

import pytest
from hypothesis import given, settings, strategies as st
from unittest.mock import AsyncMock

from app.modules.ad_performance.analyzers.recommendation_engine import RecommendationEngine


@given(
    roas=st.floats(min_value=0.5, max_value=8.0),
    spend=st.floats(min_value=1.0, max_value=10000.0),
    conversions=st.integers(min_value=0, max_value=100),
    entity_type=st.sampled_from(["adset"])
)
@settings(max_examples=100)
@pytest.mark.asyncio
async def test_property_12_recommendation_data_completeness(
    roas: float,
    spend: float,
    conversions: int,
    entity_type: str
):
    """
    **Feature: ad-performance, Property 12: Recommendation data completeness**
    
    For any generated recommendation, it should include action, target (with id and name),
    expected_impact, and confidence (0-1).
    
    **Validates: Requirements 5.1, 5.5, 10.1, 10.2, 10.3, 10.4, 10.5**
    """
    # Arrange
    engine = RecommendationEngine()
    
    # Create metrics data that will generate recommendations
    metrics_data = {
        "adsets": [
            {
                "entity_id": f"{entity_type}_123",
                "name": f"Test {entity_type.title()}",
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
    
    # Assert - verify all recommendations have complete data
    for rec in recommendations:
        # Check action field
        assert rec.action in [
            "pause_adset",
            "increase_budget",
            "decrease_budget",
            "refresh_creative"
        ], f"Invalid action: {rec.action}"
        
        # Check target field completeness
        assert rec.target is not None, "Missing target"
        assert rec.target.type in ["campaign", "adset", "ad"], f"Invalid target type: {rec.target.type}"
        assert rec.target.id is not None and rec.target.id != "", "Missing target id"
        assert rec.target.name is not None and rec.target.name != "", "Missing target name"
        
        # Check expected_impact field
        assert rec.expected_impact is not None, "Missing expected_impact"
        
        # At least one impact metric should be present
        has_impact = (
            rec.expected_impact.spend_reduction is not None or
            rec.expected_impact.spend_increase is not None or
            rec.expected_impact.revenue_increase is not None or
            rec.expected_impact.roas_improvement is not None or
            rec.expected_impact.ctr_improvement is not None
        )
        assert has_impact, "No impact metrics in expected_impact"
        
        # Check confidence field
        assert rec.confidence is not None, "Missing confidence"
        assert 0.0 <= rec.confidence <= 1.0, (
            f"Confidence {rec.confidence} not in range [0, 1]"
        )
        
        # Check priority field
        assert rec.priority in ["low", "medium", "high"], f"Invalid priority: {rec.priority}"
        
        # Check reason field
        assert rec.reason is not None and rec.reason != "", "Missing reason"


@pytest.mark.asyncio
async def test_pause_recommendation_has_spend_reduction():
    """
    Test that pause recommendations include spend_reduction in expected_impact.
    """
    # Arrange
    engine = RecommendationEngine()
    
    metrics_data = {
        "adsets": [
            {
                "entity_id": "adset_low",
                "name": "Low Performer",
                "roas": 1.0,
                "spend": 500.0,
                "conversions": 10,
                "revenue": 500.0
            }
        ],
        "ads": []
    }
    
    constraints = {"min_roas_threshold": 2.0}
    
    # Act
    recommendations = await engine.generate(
        metrics_data=metrics_data,
        optimization_goal="maximize_roas",
        constraints=constraints
    )
    
    # Assert
    pause_recs = [r for r in recommendations if r.action == "pause_adset"]
    assert len(pause_recs) > 0
    
    for rec in pause_recs:
        assert rec.expected_impact.spend_reduction is not None
        assert rec.expected_impact.spend_reduction > 0


@pytest.mark.asyncio
async def test_budget_increase_has_spend_and_revenue_increase():
    """
    Test that budget increase recommendations include both spend and revenue increase.
    """
    # Arrange
    engine = RecommendationEngine()
    
    metrics_data = {
        "adsets": [
            {
                "entity_id": "adset_high",
                "name": "High Performer",
                "roas": 5.0,
                "spend": 1000.0,
                "conversions": 100,
                "revenue": 5000.0
            }
        ],
        "ads": []
    }
    
    constraints = {"min_roas_threshold": 2.0}
    
    # Act
    recommendations = await engine.generate(
        metrics_data=metrics_data,
        optimization_goal="maximize_roas",
        constraints=constraints
    )
    
    # Assert
    budget_recs = [r for r in recommendations if r.action == "increase_budget"]
    assert len(budget_recs) > 0
    
    for rec in budget_recs:
        assert rec.expected_impact.spend_increase is not None
        assert rec.expected_impact.spend_increase > 0
        assert rec.expected_impact.revenue_increase is not None
        assert rec.expected_impact.revenue_increase > 0


@pytest.mark.asyncio
async def test_creative_refresh_has_ctr_improvement():
    """
    Test that creative refresh recommendations include CTR improvement.
    """
    # Arrange
    engine = RecommendationEngine()
    
    baseline_ctr = 0.08
    recent_ctr = 0.04
    
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
    
    metrics_data = {
        "adsets": [],
        "ads": [
            {
                "entity_id": "ad_fatigued",
                "name": "Fatigued Ad",
                "ctr": recent_ctr,
                "spend": 400.0,
                "impressions": 10000,
                "clicks": 400
            }
        ]
    }
    
    # Act
    recommendations = await engine.generate(
        metrics_data=metrics_data,
        optimization_goal="maximize_roas",
        constraints={}
    )
    
    # Assert
    refresh_recs = [r for r in recommendations if r.action == "refresh_creative"]
    assert len(refresh_recs) > 0
    
    for rec in refresh_recs:
        assert rec.expected_impact.ctr_improvement is not None
        assert rec.target.type == "ad"


@pytest.mark.asyncio
async def test_all_recommendations_sorted_by_priority():
    """
    Test that recommendations are sorted by priority (high > medium > low).
    """
    # Arrange
    engine = RecommendationEngine()
    
    # Mock to return historical data for creative fatigue
    async def mock_get_historical(*args, **kwargs):
        return [
            {"ctr": 0.08, "roas": 2.5, "spend": 100},
            {"ctr": 0.08, "roas": 2.5, "spend": 100},
            {"ctr": 0.08, "roas": 2.5, "spend": 100},
            {"ctr": 0.04, "roas": 2.5, "spend": 100},
        ]
    
    engine._get_historical_performance = mock_get_historical
    engine.mcp_client = AsyncMock()
    
    # Create data that generates multiple types of recommendations
    metrics_data = {
        "adsets": [
            {
                "entity_id": "adset_low",
                "name": "Low Performer",
                "roas": 1.0,
                "spend": 500.0,
                "conversions": 10,
                "revenue": 500.0
            },
            {
                "entity_id": "adset_high",
                "name": "High Performer",
                "roas": 5.0,
                "spend": 1000.0,
                "conversions": 100,
                "revenue": 5000.0
            }
        ],
        "ads": [
            {
                "entity_id": "ad_fatigued",
                "name": "Fatigued Ad",
                "ctr": 0.04,
                "spend": 400.0,
                "impressions": 10000,
                "clicks": 400
            }
        ]
    }
    
    constraints = {"min_roas_threshold": 2.0}
    
    # Act
    recommendations = await engine.generate(
        metrics_data=metrics_data,
        optimization_goal="maximize_roas",
        constraints=constraints
    )
    
    # Assert - verify sorting
    priority_order = {"high": 0, "medium": 1, "low": 2}
    
    for i in range(len(recommendations) - 1):
        current_priority = priority_order[recommendations[i].priority]
        next_priority = priority_order[recommendations[i + 1].priority]
        assert current_priority <= next_priority, (
            f"Recommendations not sorted by priority: "
            f"{recommendations[i].priority} before {recommendations[i + 1].priority}"
        )


@pytest.mark.asyncio
async def test_confidence_calculation_within_bounds():
    """
    Test that confidence scores are always between 0 and 1.
    """
    # Arrange
    engine = RecommendationEngine()
    
    # Test with various entity configurations
    test_entities = [
        {"entity_id": "1", "roas": 0.5, "spend": 10, "conversions": 1},
        {"entity_id": "2", "roas": 1.5, "spend": 100, "conversions": 10},
        {"entity_id": "3", "roas": 3.0, "spend": 1000, "conversions": 50},
        {"entity_id": "4", "roas": 6.0, "spend": 5000, "conversions": 200},
    ]
    
    for entity in test_entities:
        confidence = engine._calculate_confidence(entity, "pause")
        assert 0.0 <= confidence <= 1.0, (
            f"Confidence {confidence} out of bounds for entity {entity}"
        )
