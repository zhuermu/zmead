"""
Property-based tests for Ad Performance data models.

**Feature: ad-performance, Property 1: Data fetch returns complete structure**
**Validates: Requirements 1.1, 1.2, 1.3**
"""

import pytest
from datetime import date
from hypothesis import given, settings, HealthCheck
import hypothesis.strategies as st

from app.modules.ad_performance import AdPerformance


# Strategy for generating valid platforms
platform_strategy = st.sampled_from(["meta", "tiktok", "google"])

# Strategy for generating valid date ranges
date_strategy = st.dates(min_value=date(2024, 1, 1), max_value=date(2024, 12, 31))

# Strategy for generating valid levels
levels_strategy = st.lists(
    st.sampled_from(["campaign", "adset", "ad"]), min_size=1, max_size=3, unique=True
)

# Strategy for generating valid metrics
metrics_strategy = st.lists(
    st.sampled_from(["spend", "impressions", "clicks", "conversions", "revenue"]),
    min_size=1,
    max_size=5,
    unique=True,
)


@given(
    platform=platform_strategy,
    start_date=date_strategy,
    end_date=date_strategy,
    levels=levels_strategy,
    metrics=metrics_strategy,
)
@settings(
    max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@pytest.mark.asyncio
async def test_property_1_fetch_returns_complete_structure(
    platform, start_date, end_date, levels, metrics, ad_performance, sample_context
):
    """
    **Feature: ad-performance, Property 1: Data fetch returns complete structure**

    For any platform (meta/tiktok/google) and date range, calling fetch_ad_data
    should return data containing campaigns, adsets, and ads three-level data,
    and each entity should contain required metrics like spend, impressions,
    clicks, conversions, revenue.

    **Validates: Requirements 1.1, 1.2, 1.3**
    """
    # Arrange: Ensure start_date <= end_date
    if end_date < start_date:
        start_date, end_date = end_date, start_date

    # Act: Call fetch_ad_data
    result = await ad_performance.execute(
        action="fetch_ad_data",
        parameters={
            "platform": platform,
            "date_range": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
            "levels": levels,
            "metrics": metrics,
        },
        context=sample_context,
    )

    # Assert: Verify response structure
    assert result["status"] == "success", f"Expected success status, got {result['status']}"
    assert "data" in result, "Response should contain 'data' field"

    data = result["data"]

    # Verify three-level structure exists
    assert "campaigns" in data, "Data should contain 'campaigns' field"
    assert "adsets" in data, "Data should contain 'adsets' field"
    assert "ads" in data, "Data should contain 'ads' field"

    # Verify data types
    assert isinstance(data["campaigns"], list), "campaigns should be a list"
    assert isinstance(data["adsets"], list), "adsets should be a list"
    assert isinstance(data["ads"], list), "ads should be a list"

    # For each level that was requested, verify entities contain required metrics
    level_map = {"campaign": "campaigns", "adset": "adsets", "ad": "ads"}

    for level in levels:
        entities = data[level_map[level]]

        # If there are entities, verify they have the required structure
        for entity in entities:
            # Each entity should have basic identification
            assert "entity_id" in entity or f"{level}_id" in entity, (
                f"Entity should have entity_id or {level}_id"
            )
            assert "name" in entity or f"{level}_name" in entity, (
                f"Entity should have name or {level}_name"
            )

            # Each entity should have the requested metrics
            for metric in metrics:
                assert metric in entity, f"Entity should contain metric '{metric}'"

                # Verify metric values are valid
                value = entity[metric]
                if metric in ["spend", "revenue"]:
                    assert isinstance(value, (int, float)), (
                        f"{metric} should be numeric"
                    )
                    assert value >= 0, f"{metric} should be non-negative"
                elif metric in ["impressions", "clicks", "conversions"]:
                    assert isinstance(value, int), f"{metric} should be an integer"
                    assert value >= 0, f"{metric} should be non-negative"
