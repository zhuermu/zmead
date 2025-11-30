"""Tests for the Ad Performance (Reporting) module integration.

This module tests the reporting_node implementation including:
- Integration with AdPerformance module
- Credit management
- Error handling
- Action routing

Requirements: 需求 8.1-8.5, Task 14
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.nodes.reporting_node import (
    reporting_node,
    estimate_reporting_cost,
    map_action_type,
    CREDIT_COSTS,
)


class TestCreditCostEstimation:
    """Test credit cost estimation for reporting actions."""

    def test_get_report_cost(self):
        """Test cost for get_report action."""
        cost = estimate_reporting_cost("get_report", {})
        assert cost == CREDIT_COSTS["get_report"]
        assert cost == 1.0

    def test_analyze_performance_cost(self):
        """Test cost for analyze_performance action."""
        cost = estimate_reporting_cost("analyze_performance", {})
        assert cost == CREDIT_COSTS["analyze_performance"]
        assert cost == 2.0

    def test_detect_anomaly_cost(self):
        """Test cost for detect_anomaly action."""
        cost = estimate_reporting_cost("detect_anomaly", {})
        assert cost == CREDIT_COSTS["detect_anomaly"]
        assert cost == 1.5

    def test_generate_recommendations_cost(self):
        """Test cost for generate_recommendations action."""
        cost = estimate_reporting_cost("generate_recommendations", {})
        assert cost == CREDIT_COSTS["generate_recommendations"]
        assert cost == 2.0

    def test_export_report_cost(self):
        """Test cost for export_report action."""
        cost = estimate_reporting_cost("export_report", {})
        assert cost == CREDIT_COSTS["export_report"]
        assert cost == 1.0

    def test_get_metrics_summary_cost(self):
        """Test cost for get_metrics_summary action."""
        cost = estimate_reporting_cost("get_metrics_summary", {})
        assert cost == CREDIT_COSTS["get_metrics_summary"]
        assert cost == 0.5

    def test_unknown_action_default_cost(self):
        """Test default cost for unknown action."""
        cost = estimate_reporting_cost("unknown_action", {})
        assert cost == 1.0


class TestActionMapping:
    """Test action type mapping."""

    def test_get_report_mapping(self):
        """Test get_report maps to get_metrics_summary."""
        mapped = map_action_type("get_report")
        assert mapped == "get_metrics_summary"

    def test_analyze_performance_mapping(self):
        """Test analyze_performance maps to itself."""
        mapped = map_action_type("analyze_performance")
        assert mapped == "analyze_performance"

    def test_detect_anomaly_mapping(self):
        """Test detect_anomaly maps to detect_anomalies."""
        mapped = map_action_type("detect_anomaly")
        assert mapped == "detect_anomalies"

    def test_generate_recommendations_mapping(self):
        """Test generate_recommendations maps to itself."""
        mapped = map_action_type("generate_recommendations")
        assert mapped == "generate_recommendations"

    def test_export_report_mapping(self):
        """Test export_report maps to itself."""
        mapped = map_action_type("export_report")
        assert mapped == "export_report"

    def test_unknown_action_mapping(self):
        """Test unknown action maps to itself."""
        mapped = map_action_type("unknown_action")
        assert mapped == "unknown_action"


class TestReportingNodeIntegration:
    """Test reporting_node integration with AdPerformance module."""

    @pytest.mark.asyncio
    async def test_no_actions(self):
        """Test reporting_node with no pending actions."""
        state = {
            "user_id": "test_user",
            "session_id": "test_session",
            "pending_actions": [],
        }
        
        result = await reporting_node(state)
        
        assert result["completed_results"] == []

    @pytest.mark.asyncio
    async def test_insufficient_credits(self):
        """Test reporting_node with insufficient credits."""
        state = {
            "user_id": "test_user",
            "session_id": "test_session",
            "pending_actions": [
                {
                    "module": "reporting",
                    "type": "get_report",
                    "params": {"date_range": "last_7_days"},
                }
            ],
        }
        
        # Mock MCP client to raise InsufficientCreditsError
        with patch("app.nodes.reporting_node.MCPClient") as mock_mcp_class:
            mock_mcp = AsyncMock()
            mock_mcp.__aenter__.return_value = mock_mcp
            mock_mcp.__aexit__.return_value = None
            mock_mcp_class.return_value = mock_mcp
            
            from app.services.mcp_client import InsufficientCreditsError
            mock_mcp.check_credit.side_effect = InsufficientCreditsError(
                "Insufficient credits",
                required=1.0,
                available=0.0,
            )
            
            result = await reporting_node(state)
            
            assert len(result["completed_results"]) == 1
            assert result["completed_results"][0]["status"] == "error"
            assert result["completed_results"][0]["cost"] == 0

    @pytest.mark.asyncio
    async def test_successful_execution(self):
        """Test successful reporting_node execution."""
        state = {
            "user_id": "test_user",
            "session_id": "test_session",
            "pending_actions": [
                {
                    "module": "reporting",
                    "type": "get_report",
                    "params": {"date_range": {"start_date": "2024-11-20", "end_date": "2024-11-26"}},
                }
            ],
        }
        
        # Mock MCP client and AdPerformance
        with patch("app.nodes.reporting_node.MCPClient") as mock_mcp_class, \
             patch("app.nodes.reporting_node.AdPerformance") as mock_ad_perf_class:
            
            # Setup MCP mock
            mock_mcp = AsyncMock()
            mock_mcp.__aenter__.return_value = mock_mcp
            mock_mcp.__aexit__.return_value = None
            mock_mcp_class.return_value = mock_mcp
            mock_mcp.check_credit.return_value = None
            mock_mcp.deduct_credit.return_value = None
            
            # Setup AdPerformance mock
            mock_ad_perf = AsyncMock()
            mock_ad_perf_class.return_value = mock_ad_perf
            mock_ad_perf.execute.return_value = {
                "status": "success",
                "data": {
                    "summary": {
                        "total_spend": 500.0,
                        "total_revenue": 1350.0,
                        "overall_roas": 2.7,
                    },
                },
                "message": "Report generated successfully",
            }
            
            result = await reporting_node(state)
            
            # Verify result
            assert len(result["completed_results"]) == 1
            assert result["completed_results"][0]["status"] == "success"
            assert result["completed_results"][0]["module"] == "reporting"
            assert result["completed_results"][0]["cost"] == 1.0
            assert result["completed_results"][0]["mock"] is False
            
            # Verify AdPerformance was called correctly
            mock_ad_perf.execute.assert_called_once()
            call_args = mock_ad_perf.execute.call_args
            assert call_args[1]["action"] == "get_metrics_summary"
            assert call_args[1]["context"]["user_id"] == "test_user"
            assert call_args[1]["context"]["session_id"] == "test_session"
            
            # Verify credit was checked and deducted
            mock_mcp.check_credit.assert_called_once()
            mock_mcp.deduct_credit.assert_called_once()

    @pytest.mark.asyncio
    async def test_ad_performance_error(self):
        """Test reporting_node when AdPerformance raises error."""
        state = {
            "user_id": "test_user",
            "session_id": "test_session",
            "pending_actions": [
                {
                    "module": "reporting",
                    "type": "get_report",
                    "params": {"date_range": "last_7_days"},
                }
            ],
        }
        
        # Mock MCP client and AdPerformance
        with patch("app.nodes.reporting_node.MCPClient") as mock_mcp_class, \
             patch("app.nodes.reporting_node.AdPerformance") as mock_ad_perf_class:
            
            # Setup MCP mock
            mock_mcp = AsyncMock()
            mock_mcp.__aenter__.return_value = mock_mcp
            mock_mcp.__aexit__.return_value = None
            mock_mcp_class.return_value = mock_mcp
            mock_mcp.check_credit.return_value = None
            
            # Setup AdPerformance mock to raise error
            mock_ad_perf = AsyncMock()
            mock_ad_perf_class.return_value = mock_ad_perf
            mock_ad_perf.execute.side_effect = Exception("Test error")
            
            result = await reporting_node(state)
            
            # Verify error result
            assert len(result["completed_results"]) == 1
            assert result["completed_results"][0]["status"] == "error"
            assert result["completed_results"][0]["cost"] == 0
            
            # Verify credit was not deducted
            mock_mcp.deduct_credit.assert_not_called()

    @pytest.mark.asyncio
    async def test_with_notifications(self):
        """Test reporting_node with notifications in response."""
        state = {
            "user_id": "test_user",
            "session_id": "test_session",
            "pending_actions": [
                {
                    "module": "reporting",
                    "type": "get_report",
                    "params": {"date_range": "last_7_days"},
                }
            ],
        }
        
        # Mock MCP client and AdPerformance
        with patch("app.nodes.reporting_node.MCPClient") as mock_mcp_class, \
             patch("app.nodes.reporting_node.AdPerformance") as mock_ad_perf_class:
            
            # Setup MCP mock
            mock_mcp = AsyncMock()
            mock_mcp.__aenter__.return_value = mock_mcp
            mock_mcp.__aexit__.return_value = None
            mock_mcp_class.return_value = mock_mcp
            mock_mcp.check_credit.return_value = None
            mock_mcp.deduct_credit.return_value = None
            
            # Setup AdPerformance mock with notifications
            mock_ad_perf = AsyncMock()
            mock_ad_perf_class.return_value = mock_ad_perf
            mock_ad_perf.execute.return_value = {
                "status": "success",
                "data": {"summary": {}},
                "notifications": [
                    {
                        "type": "daily_report",
                        "priority": "normal",
                        "title": "Report generated",
                        "message": "Your report is ready",
                    }
                ],
            }
            
            result = await reporting_node(state)
            
            # Verify notifications are included
            assert len(result["completed_results"]) == 1
            assert "notifications" in result["completed_results"][0]
            assert len(result["completed_results"][0]["notifications"]) == 1
            assert result["completed_results"][0]["notifications"][0]["type"] == "daily_report"
