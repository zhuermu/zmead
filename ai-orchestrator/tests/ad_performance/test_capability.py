"""
Tests for AdPerformance capability module.

Tests the main entry point, action routing, error handling, and logging.
"""

import pytest
from unittest.mock import AsyncMock

from app.modules.ad_performance import AdPerformance


@pytest.mark.asyncio
async def test_execute_unknown_action(ad_performance, sample_context):
    """Test that unknown actions return proper error response"""
    result = await ad_performance.execute(
        action="unknown_action",
        parameters={},
        context=sample_context,
    )
    
    assert result["status"] == "error"
    assert result["error"]["code"] == "1001"
    assert result["error"]["type"] == "INVALID_ACTION"
    assert "unknown_action" in result["error"]["message"].lower()
    assert "supported_actions" in result["error"]["details"]


@pytest.mark.asyncio
async def test_execute_fetch_ad_data(ad_performance, sample_context):
    """Test fetch_ad_data action routing"""
    result = await ad_performance.execute(
        action="fetch_ad_data",
        parameters={
            "platform": "meta",
            "date_range": {
                "start_date": "2024-11-20",
                "end_date": "2024-11-26",
            },
        },
        context=sample_context,
    )
    
    assert result["status"] == "success"
    assert "data" in result
    assert "campaigns" in result["data"]
    assert "adsets" in result["data"]
    assert "ads" in result["data"]


@pytest.mark.asyncio
async def test_execute_generate_daily_report(ad_performance, sample_context):
    """Test generate_daily_report action routing"""
    result = await ad_performance.execute(
        action="generate_daily_report",
        parameters={
            "date": "2024-11-25",
            "include_ai_analysis": True,
        },
        context=sample_context,
    )
    
    assert result["status"] == "success"
    assert "report" in result


@pytest.mark.asyncio
async def test_execute_analyze_performance(ad_performance, sample_context):
    """Test analyze_performance action routing"""
    result = await ad_performance.execute(
        action="analyze_performance",
        parameters={
            "entity_type": "campaign",
            "entity_id": "campaign_123",
            "date_range": {
                "start_date": "2024-11-20",
                "end_date": "2024-11-26",
            },
            "comparison_period": "previous_week",
        },
        context=sample_context,
    )
    
    assert result["status"] == "success"
    assert "analysis" in result


@pytest.mark.asyncio
async def test_execute_detect_anomalies(ad_performance, sample_context):
    """Test detect_anomalies action routing"""
    result = await ad_performance.execute(
        action="detect_anomalies",
        parameters={
            "metrics": ["roas", "cpa"],
            "sensitivity": "medium",
        },
        context=sample_context,
    )
    
    assert result["status"] == "success"
    assert "anomalies" in result


@pytest.mark.asyncio
async def test_execute_generate_recommendations(ad_performance, sample_context):
    """Test generate_recommendations action routing"""
    result = await ad_performance.execute(
        action="generate_recommendations",
        parameters={
            "optimization_goal": "maximize_roas",
        },
        context=sample_context,
    )
    
    assert result["status"] == "success"
    assert "recommendations" in result


@pytest.mark.asyncio
async def test_execute_export_report(ad_performance, sample_context):
    """Test export_report action routing"""
    result = await ad_performance.execute(
        action="export_report",
        parameters={
            "report_type": "daily",
            "format": "pdf",
        },
        context=sample_context,
    )
    
    assert result["status"] == "success"
    assert "download_url" in result


@pytest.mark.asyncio
async def test_execute_get_metrics_summary(ad_performance, sample_context):
    """Test get_metrics_summary action routing"""
    result = await ad_performance.execute(
        action="get_metrics_summary",
        parameters={
            "date_range": {
                "start_date": "2024-11-26",
                "end_date": "2024-11-26",
            },
        },
        context=sample_context,
    )
    
    assert result["status"] == "success"
    assert "summary" in result


@pytest.mark.asyncio
async def test_initialization_with_dependencies(
    mock_mcp_client, mock_gemini_client, mock_redis_client
):
    """Test that AdPerformance initializes correctly with dependencies"""
    ad_perf = AdPerformance(
        mcp_client=mock_mcp_client,
        gemini_client=mock_gemini_client,
        redis_client=mock_redis_client,
    )
    
    assert ad_perf.mcp_client is mock_mcp_client
    assert ad_perf.gemini_client is mock_gemini_client
    assert ad_perf.redis_client is mock_redis_client
    assert ad_perf.cache_manager is not None
    assert ad_perf.cache_manager.cache_ttl == 300
