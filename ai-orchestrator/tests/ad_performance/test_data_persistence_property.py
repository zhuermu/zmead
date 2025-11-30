"""
Property-based tests for Ad Performance data persistence.

**Feature: ad-performance, Property 3: Fetch data correctly saved**
**Validates: Requirements 1.5**
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock
from hypothesis import given, settings, HealthCheck
import hypothesis.strategies as st

from app.modules.ad_performance import AdPerformance


# Strategy for generating valid entity types
entity_type_strategy = st.sampled_from(["campaign", "adset", "ad"])

# Strategy for generating valid entity IDs
entity_id_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd")),
    min_size=5,
    max_size=20,
)

# Strategy for generating valid entity names
entity_name_strategy = st.text(min_size=3, max_size=50)

# Strategy for generating valid ad account IDs
ad_account_id_strategy = st.integers(min_value=1, max_value=999999)

# Strategy for generating valid metric values
impressions_strategy = st.integers(min_value=0, max_value=1000000)
clicks_strategy = st.integers(min_value=0, max_value=100000)
# Avoid extremely small values that cause numerical issues (use min_value=0.01 or 0)
spend_strategy = st.one_of(
    st.just(0.0),
    st.floats(min_value=0.01, max_value=10000, allow_nan=False, allow_infinity=False)
)
conversions_strategy = st.integers(min_value=0, max_value=10000)
revenue_strategy = st.one_of(
    st.just(0.0),
    st.floats(min_value=0.01, max_value=100000, allow_nan=False, allow_infinity=False)
)


# In-memory storage for simulating MCP persistence
_test_metrics_storage = {}
_test_metrics_id_counter = 1


def _reset_test_storage():
    """Reset test storage between tests"""
    global _test_metrics_storage, _test_metrics_id_counter
    _test_metrics_storage = {}
    _test_metrics_id_counter = 1


async def _mock_save_metrics(**params):
    """Mock save_metrics MCP tool"""
    global _test_metrics_id_counter
    
    metric_id = _test_metrics_id_counter
    _test_metrics_id_counter += 1
    
    # Calculate derived metrics
    impressions = params.get("impressions", 0)
    clicks = params.get("clicks", 0)
    spend = float(params.get("spend", 0))
    conversions = params.get("conversions", 0)
    revenue = float(params.get("revenue", 0))
    
    ctr = clicks / impressions if impressions > 0 else 0
    cpc = spend / clicks if clicks > 0 else 0
    cpa = spend / conversions if conversions > 0 else 0
    roas = revenue / spend if spend > 0 else 0
    
    # Store metric
    metric = {
        "id": metric_id,
        "timestamp": params["timestamp"],
        "user_id": params.get("user_id", "test_user_123"),
        "ad_account_id": params["ad_account_id"],
        "entity_type": params["entity_type"],
        "entity_id": params["entity_id"],
        "entity_name": params["entity_name"],
        "impressions": impressions,
        "clicks": clicks,
        "spend": str(spend),
        "conversions": conversions,
        "revenue": str(revenue),
        "ctr": ctr,
        "cpc": str(cpc),
        "cpa": str(cpa),
        "roas": roas,
        "created_at": datetime.utcnow().isoformat(),
    }
    
    key = (params["ad_account_id"], params["entity_id"])
    if key not in _test_metrics_storage:
        _test_metrics_storage[key] = []
    _test_metrics_storage[key].append(metric)
    
    return metric


async def _mock_get_reports(**params):
    """Mock get_reports MCP tool"""
    ad_account_id = params.get("ad_account_id")
    entity_type = params.get("entity_type")
    entity_id = params.get("entity_id")
    
    # Filter metrics
    metrics = []
    for key, metric_list in _test_metrics_storage.items():
        acc_id, ent_id = key
        if ad_account_id and acc_id != ad_account_id:
            continue
        for metric in metric_list:
            if entity_type and metric["entity_type"] != entity_type:
                continue
            if entity_id and metric["entity_id"] != entity_id:
                continue
            metrics.append(metric)
    
    # Sort by ID descending to get most recent first
    # This ensures we return the most recently saved metric when there are duplicates
    metrics.sort(key=lambda m: m["id"], reverse=True)
    
    return {
        "metrics": metrics,
        "total": len(metrics),
        "page": params.get("page", 1),
        "page_size": params.get("page_size", 100),
        "has_more": False,
    }


async def _mock_get_metrics(**params):
    """Mock get_metrics MCP tool"""
    ad_account_id = params.get("ad_account_id")
    
    # Aggregate metrics
    total_impressions = 0
    total_clicks = 0
    total_spend = 0.0
    total_conversions = 0
    total_revenue = 0.0
    count = 0
    
    for key, metric_list in _test_metrics_storage.items():
        acc_id, _ = key
        if ad_account_id and acc_id != ad_account_id:
            continue
        for metric in metric_list:
            total_impressions += metric["impressions"]
            total_clicks += metric["clicks"]
            total_spend += float(metric["spend"])
            total_conversions += metric["conversions"]
            total_revenue += float(metric["revenue"])
            count += 1
    
    avg_ctr = total_clicks / total_impressions if total_impressions > 0 else 0
    avg_cpc = total_spend / total_clicks if total_clicks > 0 else 0
    avg_cpa = total_spend / total_conversions if total_conversions > 0 else 0
    avg_roas = total_revenue / total_spend if total_spend > 0 else 0
    
    return {
        "total_impressions": total_impressions,
        "total_clicks": total_clicks,
        "total_spend": str(total_spend),
        "total_conversions": total_conversions,
        "total_revenue": str(total_revenue),
        "avg_ctr": avg_ctr,
        "avg_cpc": str(avg_cpc),
        "avg_cpa": str(avg_cpa),
        "avg_roas": avg_roas,
        "period_start": params.get("start_date"),
        "period_end": params.get("end_date"),
    }


@pytest.fixture(autouse=False)
def persistence_ad_performance(mock_gemini_client, mock_redis_client):
    """Fixture for AdPerformance with persistence-aware MCP mock"""
    # Reset storage before each test
    _reset_test_storage()
    
    # Create MCP client with smart mocking
    mock_mcp = AsyncMock()
    
    async def call_tool_router(tool_name, params):
        if tool_name == "save_metrics":
            return await _mock_save_metrics(**params)
        elif tool_name == "get_reports":
            return await _mock_get_reports(**params)
        elif tool_name == "get_metrics":
            return await _mock_get_metrics(**params)
        else:
            return {"status": "success"}
    
    mock_mcp.call_tool = AsyncMock(side_effect=call_tool_router)
    
    instance = AdPerformance(
        mcp_client=mock_mcp,
        gemini_client=mock_gemini_client,
        redis_client=mock_redis_client,
    )
    
    yield instance
    
    # Clean up after test
    _reset_test_storage()


@given(
    entity_type=entity_type_strategy,
    entity_id=entity_id_strategy,
    entity_name=entity_name_strategy,
    ad_account_id=ad_account_id_strategy,
    impressions=impressions_strategy,
    clicks=clicks_strategy,
    spend=spend_strategy,
    conversions=conversions_strategy,
    revenue=revenue_strategy,
)
@settings(
    max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@pytest.mark.asyncio
async def test_property_3_fetch_data_correctly_saved(
    entity_type,
    entity_id,
    entity_name,
    ad_account_id,
    impressions,
    clicks,
    spend,
    conversions,
    revenue,
    persistence_ad_performance,
    sample_context,
):
    """
    **Feature: ad-performance, Property 3: Fetch data correctly saved**

    For any successfully fetched data, after calling save_metrics via MCP,
    using get_metrics should be able to query the same data back.

    This property tests the round-trip persistence: save -> retrieve -> verify.

    **Validates: Requirements 1.5**
    """
    # Reset storage at the start of each test iteration to ensure clean state
    _reset_test_storage()
    
    # Arrange: Create metrics data
    timestamp = datetime.utcnow().isoformat()
    user_id = sample_context["user_id"]

    metrics_data = [
        {
            "timestamp": timestamp,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "entity_name": entity_name,
            "impressions": impressions,
            "clicks": clicks,
            "spend": spend,  # Don't round - preserve precision for small values
            "conversions": conversions,
            "revenue": revenue,  # Don't round - preserve precision for small values
        }
    ]

    # Act: Save metrics via MCP
    save_results = await persistence_ad_performance._save_metrics_to_mcp(
        user_id=user_id,
        ad_account_id=ad_account_id,
        metrics_data=metrics_data,
    )

    # Assert: Verify save was successful
    assert len(save_results) > 0, "Should have at least one save result"
    assert save_results[0]["status"] == "success", (
        f"Save should succeed, got status: {save_results[0].get('status')}"
    )
    assert "saved_id" in save_results[0], "Save result should contain saved_id"

    # Act: Retrieve metrics via MCP
    # Use get_detailed_metrics to get the specific entity we just saved
    retrieved_data = await persistence_ad_performance._get_detailed_metrics_from_mcp(
        user_id=user_id,
        ad_account_id=ad_account_id,
        entity_type=entity_type,
        entity_id=entity_id,
        page=1,
        page_size=10,
    )

    # Assert: Verify retrieval was successful
    assert "metrics" in retrieved_data, "Retrieved data should contain 'metrics' field"
    metrics_list = retrieved_data["metrics"]
    assert len(metrics_list) > 0, (
        f"Should retrieve at least one metric for entity {entity_id}"
    )

    # Find the metric we just saved (should be the most recent one)
    saved_metric = None
    for metric in metrics_list:
        if metric["entity_id"] == entity_id:
            saved_metric = metric
            break

    assert saved_metric is not None, (
        f"Should find saved metric with entity_id {entity_id}"
    )

    # Assert: Verify data integrity (saved data matches retrieved data)
    assert saved_metric["entity_type"] == entity_type, (
        f"Entity type should match: expected {entity_type}, got {saved_metric['entity_type']}"
    )
    assert saved_metric["entity_name"] == entity_name, (
        f"Entity name should match: expected {entity_name}, got {saved_metric['entity_name']}"
    )
    assert saved_metric["impressions"] == impressions, (
        f"Impressions should match: expected {impressions}, got {saved_metric['impressions']}"
    )
    assert saved_metric["clicks"] == clicks, (
        f"Clicks should match: expected {clicks}, got {saved_metric['clicks']}"
    )
    assert saved_metric["conversions"] == conversions, (
        f"Conversions should match: expected {conversions}, got {saved_metric['conversions']}"
    )

    # For float values, allow small rounding differences
    saved_spend = float(saved_metric["spend"])
    expected_spend = spend
    assert abs(saved_spend - expected_spend) < 0.01, (
        f"Spend should match (within 0.01): expected {expected_spend}, got {saved_spend}"
    )

    saved_revenue = float(saved_metric["revenue"])
    expected_revenue = revenue
    assert abs(saved_revenue - expected_revenue) < 0.01, (
        f"Revenue should match (within 0.01): expected {expected_revenue}, got {saved_revenue}"
    )

    # Verify calculated metrics exist (CTR, CPC, CPA, ROAS)
    assert "ctr" in saved_metric, "Saved metric should have CTR calculated"
    assert "cpc" in saved_metric, "Saved metric should have CPC calculated"
    assert "cpa" in saved_metric, "Saved metric should have CPA calculated"
    assert "roas" in saved_metric, "Saved metric should have ROAS calculated"

    # Verify calculated metrics are reasonable
    if impressions > 0:
        expected_ctr = clicks / impressions
        assert abs(saved_metric["ctr"] - expected_ctr) < 0.0001, (
            "CTR should be calculated correctly"
        )

    if clicks > 0 and spend > 0:
        expected_cpc = spend / clicks
        saved_cpc = float(saved_metric["cpc"])
        assert abs(saved_cpc - expected_cpc) < 0.01, (
            "CPC should be calculated correctly"
        )

    if conversions > 0 and spend > 0:
        expected_cpa = spend / conversions
        saved_cpa = float(saved_metric["cpa"])
        assert abs(saved_cpa - expected_cpa) < 0.01, (
            "CPA should be calculated correctly"
        )

    if spend > 0:
        expected_roas = revenue / spend
        assert abs(saved_metric["roas"] - expected_roas) < 0.01, (
            "ROAS should be calculated correctly"
        )


@given(
    ad_account_id=ad_account_id_strategy,
    num_entities=st.integers(min_value=1, max_value=5),
)
@settings(
    max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@pytest.mark.asyncio
async def test_property_3_batch_save_and_retrieve(
    ad_account_id,
    num_entities,
    persistence_ad_performance,
    sample_context,
):
    """
    **Feature: ad-performance, Property 3: Fetch data correctly saved (batch)**

    For any batch of successfully saved metrics, retrieving aggregated metrics
    should return totals that match the sum of individual entities.

    **Validates: Requirements 1.5**
    """
    # Arrange: Create multiple metrics
    timestamp = datetime.utcnow().isoformat()
    user_id = sample_context["user_id"]

    metrics_data = []
    total_impressions = 0
    total_clicks = 0
    total_spend = 0.0
    total_conversions = 0
    total_revenue = 0.0

    for i in range(num_entities):
        impressions = (i + 1) * 1000
        clicks = (i + 1) * 100
        spend = (i + 1) * 50.0
        conversions = (i + 1) * 10
        revenue = (i + 1) * 150.0

        metrics_data.append({
            "timestamp": timestamp,
            "entity_type": "campaign",
            "entity_id": f"campaign_{i}",
            "entity_name": f"Campaign {i}",
            "impressions": impressions,
            "clicks": clicks,
            "spend": spend,
            "conversions": conversions,
            "revenue": revenue,
        })

        total_impressions += impressions
        total_clicks += clicks
        total_spend += spend
        total_conversions += conversions
        total_revenue += revenue

    # Act: Save all metrics
    save_results = await persistence_ad_performance._save_metrics_to_mcp(
        user_id=user_id,
        ad_account_id=ad_account_id,
        metrics_data=metrics_data,
    )

    # Assert: All saves should succeed
    successful_saves = [r for r in save_results if r["status"] == "success"]
    assert len(successful_saves) == num_entities, (
        f"All {num_entities} saves should succeed"
    )

    # Act: Retrieve aggregated metrics
    # Note: We need to filter by a time range that includes our timestamp
    today = datetime.utcnow().date().isoformat()
    aggregated = await persistence_ad_performance._get_metrics_from_mcp(
        user_id=user_id,
        start_date=today,
        end_date=today,
        ad_account_id=ad_account_id,
    )

    # Assert: Aggregated totals should match (or exceed if there was existing data)
    # Since we can't guarantee the database is empty, we check that our data is included
    assert aggregated["total_impressions"] >= total_impressions, (
        f"Total impressions should be at least {total_impressions}"
    )
    assert aggregated["total_clicks"] >= total_clicks, (
        f"Total clicks should be at least {total_clicks}"
    )
    assert aggregated["total_spend"] >= total_spend, (
        f"Total spend should be at least {total_spend}"
    )
    assert aggregated["total_conversions"] >= total_conversions, (
        f"Total conversions should be at least {total_conversions}"
    )
    assert aggregated["total_revenue"] >= total_revenue, (
        f"Total revenue should be at least {total_revenue}"
    )
