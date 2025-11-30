"""
Property-based tests for multi-platform data aggregation.

**Feature: ad-performance, Property 16: Multi-platform data aggregation completeness**
**Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5**
"""

import pytest
from datetime import date
from hypothesis import given, settings, HealthCheck, assume
import hypothesis.strategies as st

from app.modules.ad_performance import AdPerformance


# Strategy for generating valid platforms
platform_strategy = st.sampled_from(["meta", "tiktok", "google"])

# Strategy for generating valid date ranges
date_strategy = st.dates(min_value=date(2024, 1, 1), max_value=date(2024, 12, 31))

# Strategy for generating metrics data
# Use min_value > 0 to avoid division by zero in derived metrics
metrics_data_strategy = st.builds(
    dict,
    platform=platform_strategy,
    spend=st.floats(min_value=0.01, max_value=10000.0),
    revenue=st.floats(min_value=0.01, max_value=50000.0),
    conversions=st.integers(min_value=1, max_value=1000),
    impressions=st.integers(min_value=1, max_value=1000000),
    clicks=st.integers(min_value=1, max_value=100000),
)

# Strategy for generating a list of metrics from multiple platforms
metrics_list_strategy = st.lists(
    metrics_data_strategy, min_size=1, max_size=20
)


@given(
    start_date=date_strategy,
    end_date=date_strategy,
    metrics_list=metrics_list_strategy,
)
@settings(
    max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@pytest.mark.asyncio
async def test_property_16_multi_platform_aggregation_completeness(
    start_date, end_date, metrics_list, ad_performance, sample_context, mock_mcp_client
):
    """
    **Feature: ad-performance, Property 16: Multi-platform data aggregation completeness**

    For any multi-platform data, calling get_metrics_summary should return a summary
    containing total (overall metrics) and by_platform (grouped by platform), and
    the total should equal the sum of all platforms.

    **Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5**
    """
    # Arrange: Ensure start_date <= end_date
    if end_date < start_date:
        start_date, end_date = end_date, start_date

    # Ensure we have at least some data
    assume(len(metrics_list) > 0)

    # Mock MCP client to return our test metrics
    mock_mcp_client.call_tool.return_value = {"metrics": metrics_list}

    # Act: Call get_metrics_summary
    result = await ad_performance.execute(
        action="get_metrics_summary",
        parameters={
            "date_range": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
            "group_by": "platform",
        },
        context=sample_context,
    )

    # Assert: Verify response structure
    assert result["status"] == "success", f"Expected success status, got {result}"
    assert "summary" in result, "Response should contain 'summary' field"

    summary = result["summary"]

    # Verify summary contains required fields
    assert "total" in summary, "Summary should contain 'total' field"
    assert "by_platform" in summary, "Summary should contain 'by_platform' field"

    total = summary["total"]
    by_platform = summary["by_platform"]

    # Verify total contains all required metrics
    required_metrics = ["spend", "revenue", "roas", "conversions", "cpa", "impressions", "clicks", "ctr"]
    for metric in required_metrics:
        assert metric in total, f"Total should contain '{metric}' metric"

    # Verify by_platform is a dict
    assert isinstance(by_platform, dict), "by_platform should be a dictionary"

    # Verify each platform in by_platform has all required metrics
    for platform, platform_data in by_platform.items():
        assert platform in ["meta", "tiktok", "google"], (
            f"Platform should be one of meta/tiktok/google, got {platform}"
        )
        for metric in required_metrics:
            assert metric in platform_data, (
                f"Platform {platform} should contain '{metric}' metric"
            )

    # Verify data consistency: total = sum of platforms
    # Calculate expected totals from input data
    expected_spend = sum(m["spend"] for m in metrics_list)
    expected_revenue = sum(m["revenue"] for m in metrics_list)
    expected_conversions = sum(m["conversions"] for m in metrics_list)
    expected_impressions = sum(m["impressions"] for m in metrics_list)
    expected_clicks = sum(m["clicks"] for m in metrics_list)

    # Verify spend consistency (allow small float errors)
    assert abs(total["spend"] - expected_spend) < 0.01, (
        f"Total spend {total['spend']} should equal sum of input {expected_spend}"
    )

    # Verify revenue consistency
    assert abs(total["revenue"] - expected_revenue) < 0.01, (
        f"Total revenue {total['revenue']} should equal sum of input {expected_revenue}"
    )

    # Verify conversions consistency
    assert total["conversions"] == expected_conversions, (
        f"Total conversions {total['conversions']} should equal sum of input {expected_conversions}"
    )

    # Verify impressions consistency
    assert total["impressions"] == expected_impressions, (
        f"Total impressions {total['impressions']} should equal sum of input {expected_impressions}"
    )

    # Verify clicks consistency
    assert total["clicks"] == expected_clicks, (
        f"Total clicks {total['clicks']} should equal sum of input {expected_clicks}"
    )

    # Verify platform totals sum to overall total
    platform_spend_sum = sum(p["spend"] for p in by_platform.values())
    platform_revenue_sum = sum(p["revenue"] for p in by_platform.values())
    platform_conversions_sum = sum(p["conversions"] for p in by_platform.values())

    assert abs(total["spend"] - platform_spend_sum) < 0.01, (
        f"Total spend {total['spend']} should equal sum of platform spends {platform_spend_sum}"
    )

    assert abs(total["revenue"] - platform_revenue_sum) < 0.01, (
        f"Total revenue {total['revenue']} should equal sum of platform revenues {platform_revenue_sum}"
    )

    assert total["conversions"] == platform_conversions_sum, (
        f"Total conversions {total['conversions']} should equal sum of platform conversions {platform_conversions_sum}"
    )

    # Verify derived metrics are calculated correctly
    if total["spend"] > 0:
        expected_roas = total["revenue"] / total["spend"]
        assert abs(total["roas"] - expected_roas) < 0.01, (
            f"ROAS should be revenue/spend: {expected_roas}, got {total['roas']}"
        )

    if total["conversions"] > 0:
        expected_cpa = total["spend"] / total["conversions"]
        assert abs(total["cpa"] - expected_cpa) < 0.01, (
            f"CPA should be spend/conversions: {expected_cpa}, got {total['cpa']}"
        )

    if total["impressions"] > 0:
        expected_ctr = total["clicks"] / total["impressions"]
        assert abs(total["ctr"] - expected_ctr) < 0.01, (
            f"CTR should be clicks/impressions: {expected_ctr}, got {total['ctr']}"
        )

    # Verify all numeric values are non-negative
    for metric in ["spend", "revenue", "roas", "conversions", "cpa", "impressions", "clicks", "ctr"]:
        assert total[metric] >= 0, f"Total {metric} should be non-negative"

    for platform, platform_data in by_platform.items():
        for metric in ["spend", "revenue", "roas", "conversions", "cpa", "impressions", "clicks", "ctr"]:
            assert platform_data[metric] >= 0, (
                f"Platform {platform} {metric} should be non-negative"
            )
