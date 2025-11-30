"""
Property-based tests for daily report generation.

**Feature: ad-performance, Property 4: Daily report data completeness**
**Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5**
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


@given(
    report_date=valid_dates(),
    current_metrics=metrics_data(),
    previous_metrics=metrics_data(),
    include_ai_analysis=st.booleans(),
    include_recommendations=st.booleans(),
)
@settings(max_examples=100)
@pytest.mark.asyncio
async def test_property_4_daily_report_completeness(
    report_date,
    current_metrics,
    previous_metrics,
    include_ai_analysis,
    include_recommendations,
):
    """
    **Feature: ad-performance, Property 4: Daily report data completeness**
    
    For any date, calling generate_daily_report should return a complete report
    structure containing:
    - summary (core metrics)
    - ai_analysis (AI insights) if requested
    - recommendations (optimization suggestions) if requested
    
    **Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5**
    """
    # Arrange
    mock_mcp_client = AsyncMock()
    mock_gemini_client = AsyncMock()
    
    # Mock MCP responses
    mock_mcp_client.call_tool = AsyncMock(
        side_effect=lambda tool, params: {
            "get_metrics": current_metrics,
            "get_reports": {
                "metrics": [
                    {
                        "entity_type": "adset",
                        "entity_id": "adset_1",
                        "name": "Test Adset",
                        "roas": 2.5,
                        "spend": 100.0,
                        "revenue": 250.0,
                    }
                ],
                "total": 1,
            },
        }.get(tool, {})
    )
    
    # Mock Gemini response
    mock_gemini_client.generate_content = AsyncMock(
        return_value=type('obj', (object,), {
            'text': '{"key_insights": ["Insight 1", "Insight 2"], "trends": {"roas_trend": "stable"}}'
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
            "include_ai_analysis": include_ai_analysis,
            "include_recommendations": include_recommendations,
        },
        context={"user_id": "test_user", "session_id": "test_session"},
    )
    
    # Assert - Status should be success
    assert result["status"] == "success", f"Expected success status, got {result.get('status')}"
    
    # Assert - Report should exist
    assert "report" in result, "Report should be present in result"
    report = result["report"]
    
    # Assert - Report should have date
    assert "date" in report, "Report should have date field"
    
    # Assert - Report should have summary with core metrics (Requirement 2.2)
    assert "summary" in report, "Report should have summary field"
    summary = report["summary"]
    
    # Verify all required summary fields
    required_summary_fields = [
        "total_spend",
        "total_revenue",
        "overall_roas",
        "total_conversions",
        "avg_cpa",
    ]
    for field in required_summary_fields:
        assert field in summary, f"Summary should have {field} field"
        assert isinstance(
            summary[field], (int, float)
        ), f"Summary {field} should be numeric"
    
    # Assert - Report should have ai_analysis (Requirement 2.3)
    assert "ai_analysis" in report, "Report should have ai_analysis field"
    ai_analysis = report["ai_analysis"]
    
    if include_ai_analysis:
        # When AI analysis is requested, it should have content
        assert "key_insights" in ai_analysis, "AI analysis should have key_insights"
        assert isinstance(
            ai_analysis["key_insights"], list
        ), "key_insights should be a list"
        
        assert "trends" in ai_analysis, "AI analysis should have trends"
        assert isinstance(ai_analysis["trends"], dict), "trends should be a dict"
    else:
        # When AI analysis is not requested, fields should still exist but may be empty
        assert "key_insights" in ai_analysis, "AI analysis should have key_insights field"
        assert "trends" in ai_analysis, "AI analysis should have trends field"
    
    # Assert - Report should have recommendations (Requirement 2.4)
    assert "recommendations" in report, "Report should have recommendations field"
    recommendations = report["recommendations"]
    assert isinstance(recommendations, list), "recommendations should be a list"
    
    if include_recommendations:
        # When recommendations are requested, validate structure if any exist
        for rec in recommendations:
            assert "priority" in rec, "Recommendation should have priority"
            assert rec["priority"] in [
                "low",
                "medium",
                "high",
            ], "Priority should be valid"
            
            assert "action" in rec, "Recommendation should have action"
            assert "target" in rec, "Recommendation should have target"
            assert "reason" in rec, "Recommendation should have reason"
            assert "expected_impact" in rec, "Recommendation should have expected_impact"
            assert "confidence" in rec, "Recommendation should have confidence"
            
            # Validate confidence is between 0 and 1
            assert 0 <= rec["confidence"] <= 1, "Confidence should be between 0 and 1"
    
    # Assert - Result should have message (Requirement 2.5)
    assert "message" in result, "Result should have message field"
    assert isinstance(result["message"], str), "Message should be a string"
    
    # Assert - Result should have notifications (Requirement 2.1)
    assert "notifications" in result, "Result should have notifications field"
    notifications = result["notifications"]
    assert isinstance(notifications, list), "notifications should be a list"
    
    # At minimum, there should be a daily_report notification
    assert len(notifications) > 0, "Should have at least one notification"
    
    # Verify daily_report notification structure
    daily_report_notif = next(
        (n for n in notifications if n.get("type") == "daily_report"), None
    )
    assert daily_report_notif is not None, "Should have daily_report notification"
    
    assert "priority" in daily_report_notif, "Notification should have priority"
    assert "title" in daily_report_notif, "Notification should have title"
    assert "message" in daily_report_notif, "Notification should have message"
    assert "data" in daily_report_notif, "Notification should have data"


@pytest.mark.asyncio
async def test_daily_report_with_empty_metrics():
    """Test daily report generation with empty metrics"""
    # Arrange
    mock_mcp_client = AsyncMock()
    mock_gemini_client = AsyncMock()
    
    # Mock empty metrics
    mock_mcp_client.call_tool = AsyncMock(
        side_effect=lambda tool, params: {
            "get_metrics": {
                "total_spend": 0.0,
                "total_revenue": 0.0,
                "avg_roas": 0.0,
                "total_conversions": 0,
                "avg_cpa": 0.0,
                "total_impressions": 0,
                "total_clicks": 0,
                "avg_ctr": 0.0,
                "avg_cpc": 0.0,
                "period_start": "2024-11-28",
                "period_end": "2024-11-28",
            },
            "get_reports": {"metrics": [], "total": 0},
        }.get(tool, {})
    )
    
    mock_gemini_client.generate_content = AsyncMock(
        return_value=type('obj', (object,), {
            'text': '{"key_insights": ["No data available"], "trends": {}}'
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
    assert result["status"] == "success"
    assert result["report"]["summary"]["total_spend"] == 0.0
    assert result["report"]["summary"]["total_revenue"] == 0.0
    assert len(result["report"]["recommendations"]) == 0  # No recommendations with no data

