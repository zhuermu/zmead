"""
Property-based tests for notification data formatting.

**Feature: ad-performance, Property 17: Notification data completeness and correctness**
**Validates: Requirements 9.1, 9.2, 9.3, 9.4**
"""

from datetime import date, timedelta
from unittest.mock import AsyncMock

import pytest
from hypothesis import given, settings
import hypothesis.strategies as st

from app.modules.ad_performance import AdPerformance


# Strategy for generating valid dates
@st.composite
def valid_dates(draw):
    """Generate valid dates within a reasonable range"""
    days_ago = draw(st.integers(min_value=0, max_value=365))
    return (date.today() - timedelta(days=days_ago)).isoformat()


# Strategy for generating metrics data
@st.composite
def metrics_data(draw):
    """Generate valid metrics data"""
    return {
        "total_spend": draw(st.floats(min_value=0, max_value=10000)),
        "total_revenue": draw(st.floats(min_value=0, max_value=50000)),
        "avg_roas": draw(st.floats(min_value=0, max_value=10)),
        "total_conversions": draw(st.integers(min_value=0, max_value=1000)),
        "avg_cpa": draw(st.floats(min_value=0, max_value=500)),
        "total_impressions": draw(st.integers(min_value=0, max_value=1000000)),
        "total_clicks": draw(st.integers(min_value=0, max_value=100000)),
        "avg_ctr": draw(st.floats(min_value=0, max_value=1)),
        "avg_cpc": draw(st.floats(min_value=0, max_value=50)),
        "period_start": draw(valid_dates()),
        "period_end": draw(valid_dates()),
    }


# Strategy for generating recommendations with varying priorities
@st.composite
def recommendation_data(draw):
    """Generate recommendation data with varying priorities"""
    priority = draw(st.sampled_from(["low", "medium", "high"]))
    action = draw(st.sampled_from(["pause_adset", "increase_budget", "refresh_creative"]))
    
    return {
        "entity_type": "adset",
        "entity_id": f"adset_{draw(st.integers(min_value=1, max_value=1000))}",
        "name": f"Test Adset {draw(st.integers(min_value=1, max_value=100))}",
        "roas": draw(st.floats(min_value=0.5, max_value=5.0)),
        "spend": draw(st.floats(min_value=10, max_value=1000)),
        "revenue": draw(st.floats(min_value=10, max_value=5000)),
        "priority": priority,
        "action": action,
    }


@given(
    report_date=valid_dates(),
    current_metrics=metrics_data(),
    has_high_priority_recommendations=st.booleans(),
    num_recommendations=st.integers(min_value=0, max_value=5),
)
@settings(max_examples=100)
@pytest.mark.asyncio
async def test_property_17_notification_data_completeness(
    report_date,
    current_metrics,
    has_high_priority_recommendations,
    num_recommendations,
):
    """
    **Feature: ad-performance, Property 17: Notification data completeness and correctness**
    
    For any report generation or anomaly detection result, returned notification data
    should include correct type, priority, title, message, data fields, and priority
    should be set correctly based on severity (normal/urgent).
    
    **Validates: Requirements 9.1, 9.2, 9.3, 9.4**
    """
    # Arrange
    mock_mcp_client = AsyncMock()
    mock_gemini_client = AsyncMock()
    
    # Generate recommendations based on test parameters
    recommendations = []
    if num_recommendations > 0:
        for i in range(num_recommendations):
            if has_high_priority_recommendations and i == 0:
                # First recommendation is high priority
                recommendations.append({
                    "entity_type": "adset",
                    "entity_id": f"adset_{i}",
                    "name": f"Test Adset {i}",
                    "roas": 1.0,  # Low ROAS for pause recommendation
                    "spend": 100.0,
                    "revenue": 100.0,
                })
            else:
                # Other recommendations are medium/low priority
                recommendations.append({
                    "entity_type": "adset",
                    "entity_id": f"adset_{i}",
                    "name": f"Test Adset {i}",
                    "roas": 3.0,  # Good ROAS
                    "spend": 100.0,
                    "revenue": 300.0,
                })
    
    # If we have high-priority recommendations, ensure current_metrics has meaningful data
    if has_high_priority_recommendations and num_recommendations > 0:
        # Ensure metrics have non-zero values to trigger recommendations
        if current_metrics["total_spend"] == 0:
            current_metrics["total_spend"] = 100.0
            current_metrics["total_revenue"] = 100.0
            current_metrics["avg_roas"] = 1.0
    
    # Mock MCP responses
    mock_mcp_client.call_tool = AsyncMock(
        side_effect=lambda tool, params: {
            "get_metrics": current_metrics,
            "get_reports": {
                "metrics": recommendations,
                "total": len(recommendations),
            },
        }.get(tool, {})
    )
    
    # Mock Gemini response
    mock_gemini_client.generate_content = AsyncMock(
        return_value=type('obj', (object,), {
            'text': '{"key_insights": ["Insight 1"], "trends": {"roas_trend": "stable"}}'
        })()
    )
    
    ad_performance = AdPerformance(
        mcp_client=mock_mcp_client,
        gemini_client=mock_gemini_client,
        redis_client=None,
    )
    
    # Act
    result = await ad_performance.execute(
        action="generate_daily_report",
        parameters={
            "date": report_date,
            "include_ai_analysis": True,
            "include_recommendations": True,
        },
        context={"user_id": "test_user", "session_id": "test_session"},
    )
    
    # Assert - Result should have notifications
    assert "notifications" in result, "Result should have notifications field"
    notifications = result["notifications"]
    assert isinstance(notifications, list), "notifications should be a list"
    
    # Assert - Should have at least one notification (daily_report)
    assert len(notifications) > 0, "Should have at least one notification"
    
    # Assert - Verify daily_report notification (Requirement 9.1)
    daily_report_notif = next(
        (n for n in notifications if n.get("type") == "daily_report"), None
    )
    assert daily_report_notif is not None, "Should have daily_report notification"
    
    # Verify daily_report notification structure (Requirement 9.4)
    assert "type" in daily_report_notif, "Notification should have type"
    assert daily_report_notif["type"] == "daily_report", "Type should be daily_report"
    
    assert "priority" in daily_report_notif, "Notification should have priority"
    assert daily_report_notif["priority"] == "normal", "Daily report priority should be normal"
    
    assert "title" in daily_report_notif, "Notification should have title"
    assert isinstance(daily_report_notif["title"], str), "Title should be a string"
    assert len(daily_report_notif["title"]) > 0, "Title should not be empty"
    
    assert "message" in daily_report_notif, "Notification should have message"
    assert isinstance(daily_report_notif["message"], str), "Message should be a string"
    assert len(daily_report_notif["message"]) > 0, "Message should not be empty"
    
    assert "data" in daily_report_notif, "Notification should have data"
    assert isinstance(daily_report_notif["data"], dict), "Data should be a dict"
    
    # Verify data contains required fields
    data = daily_report_notif["data"]
    assert "report_date" in data, "Data should have report_date"
    assert "summary" in data, "Data should have summary"
    
    summary = data["summary"]
    assert "total_spend" in summary, "Summary should have total_spend"
    assert "total_revenue" in summary, "Summary should have total_revenue"
    assert "overall_roas" in summary, "Summary should have overall_roas"
    
    # Assert - Verify anomaly_alert notifications for high-priority recommendations (Requirement 9.2, 9.3)
    anomaly_alerts = [n for n in notifications if n.get("type") == "anomaly_alert"]
    
    if has_high_priority_recommendations and num_recommendations > 0:
        # Should have at least one anomaly alert for high-priority recommendations
        assert len(anomaly_alerts) > 0, "Should have anomaly alerts for high-priority recommendations"
        
        for alert in anomaly_alerts:
            # Verify structure
            assert "type" in alert, "Alert should have type"
            assert alert["type"] == "anomaly_alert", "Type should be anomaly_alert"
            
            assert "priority" in alert, "Alert should have priority"
            assert alert["priority"] in ["normal", "urgent"], "Priority should be normal or urgent"
            
            assert "title" in alert, "Alert should have title"
            assert isinstance(alert["title"], str), "Title should be a string"
            assert len(alert["title"]) > 0, "Title should not be empty"
            
            assert "message" in alert, "Alert should have message"
            assert isinstance(alert["message"], str), "Message should be a string"
            assert len(alert["message"]) > 0, "Message should not be empty"
            
            assert "data" in alert, "Alert should have data"
            assert isinstance(alert["data"], dict), "Data should be a dict"
            
            # Verify data contains required fields
            alert_data = alert["data"]
            assert "action" in alert_data, "Alert data should have action"
            assert "target_type" in alert_data, "Alert data should have target_type"
            assert "target_id" in alert_data, "Alert data should have target_id"
            assert "target_name" in alert_data, "Alert data should have target_name"
            assert "reason" in alert_data, "Alert data should have reason"
            assert "confidence" in alert_data, "Alert data should have confidence"
            assert "expected_impact" in alert_data, "Alert data should have expected_impact"
            
            # Verify confidence is between 0 and 1
            assert 0 <= alert_data["confidence"] <= 1, "Confidence should be between 0 and 1"
            
            # Verify priority is set correctly based on action (Requirement 9.3)
            if alert_data["action"] == "pause_adset":
                assert alert["priority"] == "urgent", "Pause action should have urgent priority"
            else:
                assert alert["priority"] == "normal", "Other actions should have normal priority"


@pytest.mark.asyncio
async def test_notification_priority_for_pause_action():
    """Test that pause_adset recommendations generate urgent notifications"""
    # Arrange
    mock_mcp_client = AsyncMock()
    mock_gemini_client = AsyncMock()
    
    # Mock data with low ROAS to trigger pause recommendation
    mock_mcp_client.call_tool = AsyncMock(
        side_effect=lambda tool, params: {
            "get_metrics": {
                "total_spend": 100.0,
                "total_revenue": 50.0,
                "avg_roas": 0.5,
                "total_conversions": 5,
                "avg_cpa": 20.0,
                "total_impressions": 10000,
                "total_clicks": 100,
                "avg_ctr": 0.01,
                "avg_cpc": 1.0,
                "period_start": "2024-11-28",
                "period_end": "2024-11-28",
            },
            "get_detailed_metrics": {
                "metrics": [
                    {
                        "entity_type": "adset",
                        "entity_id": "adset_low_roas",
                        "name": "Low ROAS Adset",
                        "roas": 0.5,  # Very low ROAS
                        "spend": 100.0,
                        "revenue": 50.0,
                        "impressions": 10000,
                        "clicks": 100,
                        "ctr": 0.01,
                        "conversions": 5,
                        "cpa": 20.0,
                    }
                ],
                "total": 1,
                "page": 1,
                "page_size": 100,
            },
        }.get(tool, {})
    )
    
    mock_gemini_client.generate_content = AsyncMock(
        return_value=type('obj', (object,), {
            'text': '{"key_insights": ["Low ROAS detected"], "trends": {"roas_trend": "declining"}}'
        })()
    )
    
    ad_performance = AdPerformance(
        mcp_client=mock_mcp_client,
        gemini_client=mock_gemini_client,
        redis_client=None,
    )
    
    # Act
    result = await ad_performance.execute(
        action="generate_daily_report",
        parameters={
            "date": "2024-11-28",
            "include_ai_analysis": True,
            "include_recommendations": True,
        },
        context={"user_id": "test_user", "session_id": "test_session"},
    )
    
    # Assert
    notifications = result["notifications"]
    anomaly_alerts = [n for n in notifications if n.get("type") == "anomaly_alert"]
    
    # Should have at least one anomaly alert
    assert len(anomaly_alerts) > 0, "Should have anomaly alerts for low ROAS"
    
    # Verify pause_adset recommendations have urgent priority
    pause_alerts = [
        a for a in anomaly_alerts
        if a.get("data", {}).get("action") == "pause_adset"
    ]
    
    for alert in pause_alerts:
        assert alert["priority"] == "urgent", "Pause recommendations should have urgent priority"


@pytest.mark.asyncio
async def test_notification_priority_for_increase_budget_action():
    """Test that increase_budget recommendations generate normal priority notifications"""
    # Arrange
    mock_mcp_client = AsyncMock()
    mock_gemini_client = AsyncMock()
    
    # Mock data with high ROAS to trigger increase_budget recommendation
    mock_mcp_client.call_tool = AsyncMock(
        side_effect=lambda tool, params: {
            "get_metrics": {
                "total_spend": 100.0,
                "total_revenue": 400.0,
                "avg_roas": 4.0,
                "total_conversions": 50,
                "avg_cpa": 2.0,
                "total_impressions": 10000,
                "total_clicks": 500,
                "avg_ctr": 0.05,
                "avg_cpc": 0.2,
                "period_start": "2024-11-28",
                "period_end": "2024-11-28",
            },
            "get_reports": {
                "metrics": [
                    {
                        "entity_type": "adset",
                        "entity_id": "adset_high_roas",
                        "name": "High ROAS Adset",
                        "roas": 4.0,  # Very high ROAS
                        "spend": 100.0,
                        "revenue": 400.0,
                    }
                ],
                "total": 1,
            },
        }.get(tool, {})
    )
    
    mock_gemini_client.generate_content = AsyncMock(
        return_value=type('obj', (object,), {
            'text': '{"key_insights": ["High ROAS detected"], "trends": {"roas_trend": "improving"}}'
        })()
    )
    
    ad_performance = AdPerformance(
        mcp_client=mock_mcp_client,
        gemini_client=mock_gemini_client,
        redis_client=None,
    )
    
    # Act
    result = await ad_performance.execute(
        action="generate_daily_report",
        parameters={
            "date": "2024-11-28",
            "include_ai_analysis": True,
            "include_recommendations": True,
        },
        context={"user_id": "test_user", "session_id": "test_session"},
    )
    
    # Assert
    notifications = result["notifications"]
    anomaly_alerts = [n for n in notifications if n.get("type") == "anomaly_alert"]
    
    # Should have at least one anomaly alert
    assert len(anomaly_alerts) > 0, "Should have anomaly alerts for high ROAS"
    
    # Verify increase_budget recommendations have normal priority
    increase_alerts = [
        a for a in anomaly_alerts
        if a.get("data", {}).get("action") == "increase_budget"
    ]
    
    for alert in increase_alerts:
        assert alert["priority"] == "normal", "Increase budget recommendations should have normal priority"

