"""
Tests for A/B Test Manager

Tests the creation and analysis of A/B tests for creative optimization.

Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

from app.modules.campaign_automation.managers.ab_test_manager import ABTestManager
from app.modules.campaign_automation.models import (
    ABTestResult,
    ABTestVariant,
    ABTestWinner,
)


@pytest.fixture
def ab_test_manager(mock_mcp_client, mock_platform_adapter):
    """Create ABTestManager instance with mocked dependencies"""
    return ABTestManager(
        mcp_client=mock_mcp_client,
        platform_adapter=mock_platform_adapter
    )


@pytest.fixture
def sample_test_data_sufficient():
    """Sample test data with sufficient conversions"""
    return {
        "test_id": "test_123",
        "campaign_id": "campaign_456",
        "variants": [
            {
                "creative_id": "creative_1",
                "spend": 90.0,
                "revenue": 315.0,
                "roas": 3.5,
                "ctr": 0.028,
                "conversions": 150,
                "impressions": 5000
            },
            {
                "creative_id": "creative_2",
                "spend": 90.0,
                "revenue": 225.0,
                "roas": 2.5,
                "ctr": 0.021,
                "conversions": 120,
                "impressions": 5000
            },
            {
                "creative_id": "creative_3",
                "spend": 90.0,
                "revenue": 180.0,
                "roas": 2.0,
                "ctr": 0.018,
                "conversions": 100,
                "impressions": 5000
            }
        ]
    }


@pytest.fixture
def sample_test_data_insufficient():
    """Sample test data with insufficient conversions"""
    return {
        "test_id": "test_123",
        "campaign_id": "campaign_456",
        "variants": [
            {
                "creative_id": "creative_1",
                "spend": 30.0,
                "revenue": 105.0,
                "roas": 3.5,
                "ctr": 0.028,
                "conversions": 50,  # Below minimum
                "impressions": 1500
            },
            {
                "creative_id": "creative_2",
                "spend": 30.0,
                "revenue": 75.0,
                "roas": 2.5,
                "ctr": 0.021,
                "conversions": 40,  # Below minimum
                "impressions": 1500
            }
        ]
    }


@pytest.mark.asyncio
async def test_create_ab_test_success(
    ab_test_manager,
    mock_platform_adapter,
    mock_mcp_client,
    sample_ab_test_parameters,
    sample_context
):
    """
    Test successful A/B test creation
    
    Requirements: 5.1, 5.2
    """
    # Setup mock responses
    mock_platform_adapter.create_campaign.return_value = {
        "id": "campaign_123",
        "name": "Creative Test - A/B Test"
    }
    
    mock_platform_adapter.create_adset.return_value = {
        "id": "adset_123",
        "name": "Variant A"
    }
    
    mock_platform_adapter.create_ad.return_value = {
        "id": "ad_123"
    }
    
    # Execute
    result = await ab_test_manager.create_ab_test(
        test_name=sample_ab_test_parameters["test_name"],
        creative_ids=sample_ab_test_parameters["creative_ids"],
        daily_budget=sample_ab_test_parameters["daily_budget"],
        test_duration_days=sample_ab_test_parameters["test_duration_days"],
        platform=sample_ab_test_parameters["platform"],
        context=sample_context
    )
    
    # Verify
    assert result["status"] == "success"
    assert "test_id" in result
    assert result["campaign_id"] == "campaign_123"
    assert len(result["adsets"]) == 3  # 3 creatives
    
    # Verify budget split
    expected_budget_per_variant = 90.0 / 3
    for adset in result["adsets"]:
        assert adset["budget"] == expected_budget_per_variant
    
    # Verify MCP call
    mock_mcp_client.call_tool.assert_called()


@pytest.mark.asyncio
async def test_create_ab_test_budget_split(
    ab_test_manager,
    mock_platform_adapter,
    sample_context
):
    """
    Test that budget is split equally across variants
    
    Requirements: 5.2 - Property 10: A/B 测试预算均分
    """
    creative_ids = ["creative_1", "creative_2", "creative_3", "creative_4"]
    total_budget = 120.0
    
    mock_platform_adapter.create_campaign.return_value = {"id": "campaign_123"}
    mock_platform_adapter.create_adset.return_value = {"id": "adset_123"}
    mock_platform_adapter.create_ad.return_value = {"id": "ad_123"}
    
    result = await ab_test_manager.create_ab_test(
        test_name="Budget Split Test",
        creative_ids=creative_ids,
        daily_budget=total_budget,
        test_duration_days=3,
        platform="meta",
        context=sample_context
    )
    
    # Verify equal budget split
    expected_budget = total_budget / len(creative_ids)
    for adset in result["adsets"]:
        assert adset["budget"] == expected_budget


@pytest.mark.asyncio
async def test_analyze_ab_test_with_winner(
    ab_test_manager,
    mock_mcp_client,
    sample_test_data_sufficient,
    sample_context
):
    """
    Test A/B test analysis with clear winner
    
    Requirements: 5.3, 5.4, 5.6
    """
    # Mock _get_test_data to return sufficient sample data
    with patch.object(
        ab_test_manager,
        '_get_test_data',
        return_value=sample_test_data_sufficient
    ):
        result = await ab_test_manager.analyze_ab_test(
            test_id="test_123",
            context=sample_context
        )
    
    # Verify result structure
    assert isinstance(result, ABTestResult)
    assert result.test_id == "test_123"
    assert len(result.results) == 3
    
    # Verify variants are sorted by ROAS
    assert result.results[0].roas >= result.results[1].roas
    assert result.results[1].roas >= result.results[2].roas
    
    # Verify ranks
    assert result.results[0].rank == 1
    assert result.results[1].rank == 2
    assert result.results[2].rank == 3
    
    # Verify winner (if p-value < 0.05)
    if result.winner:
        assert isinstance(result.winner, ABTestWinner)
        assert result.winner.confidence == 95
        assert 0 <= result.winner.p_value <= 1
    
    # Verify recommendations
    assert len(result.recommendations) > 0


@pytest.mark.asyncio
async def test_analyze_ab_test_insufficient_samples(
    ab_test_manager,
    sample_test_data_insufficient,
    sample_context
):
    """
    Test A/B test analysis with insufficient sample size
    
    Requirements: 5.5
    """
    # Mock _get_test_data to return insufficient sample data
    with patch.object(
        ab_test_manager,
        '_get_test_data',
        return_value=sample_test_data_insufficient
    ):
        result = await ab_test_manager.analyze_ab_test(
            test_id="test_123",
            context=sample_context
        )
    
    # Verify insufficient sample handling
    assert isinstance(result, ABTestResult)
    assert result.winner is None
    assert "数据不足" in result.message
    assert any("数据不足" in rec for rec in result.recommendations)


def test_chi_square_test(ab_test_manager):
    """
    Test chi-square statistical test
    
    Requirements: 5.3
    """
    variants = [
        {
            "creative_id": "creative_1",
            "conversions": 150,
            "impressions": 5000
        },
        {
            "creative_id": "creative_2",
            "conversions": 120,
            "impressions": 5000
        },
        {
            "creative_id": "creative_3",
            "conversions": 100,
            "impressions": 5000
        }
    ]
    
    result = ab_test_manager._chi_square_test(variants)
    
    # Verify result structure
    assert "chi2" in result
    assert "p_value" in result
    assert "dof" in result
    assert "expected" in result
    
    # Verify values are valid
    assert result["chi2"] >= 0
    assert 0 <= result["p_value"] <= 1
    assert result["dof"] == 2  # (3 variants - 1) * (2 outcomes - 1)


def test_generate_recommendations_with_winner(ab_test_manager):
    """
    Test recommendation generation with clear winner
    
    Requirements: 5.6
    """
    variants = [
        ABTestVariant(
            creative_id="creative_1",
            spend=90.0,
            revenue=315.0,
            roas=3.5,
            ctr=0.028,
            conversions=150,
            impressions=5000,
            conversion_rate=0.03,
            rank=1
        ),
        ABTestVariant(
            creative_id="creative_2",
            spend=90.0,
            revenue=225.0,
            roas=2.5,
            ctr=0.021,
            conversions=120,
            impressions=5000,
            conversion_rate=0.024,
            rank=2
        ),
        ABTestVariant(
            creative_id="creative_3",
            spend=90.0,
            revenue=180.0,
            roas=2.0,
            ctr=0.018,
            conversions=100,
            impressions=5000,
            conversion_rate=0.02,
            rank=3
        )
    ]
    
    winner = ABTestWinner(
        creative_id="creative_1",
        confidence=95,
        p_value=0.03
    )
    
    recommendations = ab_test_manager._generate_recommendations(variants, winner)
    
    # Verify recommendations
    assert len(recommendations) > 0
    assert any("creative_3" in rec for rec in recommendations)  # Worst performer
    assert any("creative_1" in rec for rec in recommendations)  # Winner
    assert any("暂停" in rec for rec in recommendations)
    assert any("增加" in rec for rec in recommendations)


def test_generate_recommendations_no_winner(ab_test_manager):
    """
    Test recommendation generation without clear winner
    
    Requirements: 5.6
    """
    variants = [
        ABTestVariant(
            creative_id="creative_1",
            spend=90.0,
            revenue=270.0,
            roas=3.0,
            ctr=0.025,
            conversions=120,
            impressions=5000,
            conversion_rate=0.024,
            rank=1
        ),
        ABTestVariant(
            creative_id="creative_2",
            spend=90.0,
            revenue=260.0,
            roas=2.89,
            ctr=0.024,
            conversions=118,
            impressions=5000,
            conversion_rate=0.0236,
            rank=2
        )
    ]
    
    recommendations = ab_test_manager._generate_recommendations(variants, None)
    
    # Verify recommendations suggest continuing test
    assert len(recommendations) > 0
    assert any("差异不显著" in rec or "继续测试" in rec for rec in recommendations)


@pytest.mark.asyncio
async def test_create_ab_test_platform_error(
    ab_test_manager,
    mock_platform_adapter,
    sample_context
):
    """Test A/B test creation handles platform errors"""
    # Setup mock to raise error
    mock_platform_adapter.create_campaign.side_effect = Exception("Platform API error")
    
    # Execute and verify error is raised
    with pytest.raises(Exception) as exc_info:
        await ab_test_manager.create_ab_test(
            test_name="Error Test",
            creative_ids=["creative_1", "creative_2"],
            daily_budget=60.0,
            test_duration_days=3,
            platform="meta",
            context=sample_context
        )
    
    assert "Platform API error" in str(exc_info.value)


@pytest.mark.asyncio
async def test_analyze_ab_test_test_not_found(
    ab_test_manager,
    mock_mcp_client,
    sample_context
):
    """Test A/B test analysis handles missing test"""
    # Mock MCP to return no campaigns
    async def mock_call_tool(tool_name, params):
        if tool_name == "get_campaigns":
            return {"campaigns": []}
        return {}
    
    mock_mcp_client.call_tool = AsyncMock(side_effect=mock_call_tool)
    
    # Execute and verify error is raised
    with pytest.raises(ValueError) as exc_info:
        await ab_test_manager.analyze_ab_test(
            test_id="nonexistent_test",
            context=sample_context
        )
    
    assert "Test not found" in str(exc_info.value)


def test_chi_square_test_equal_performance(ab_test_manager):
    """Test chi-square test with equal performance (high p-value)"""
    variants = [
        {
            "creative_id": "creative_1",
            "conversions": 100,
            "impressions": 5000
        },
        {
            "creative_id": "creative_2",
            "conversions": 100,
            "impressions": 5000
        }
    ]
    
    result = ab_test_manager._chi_square_test(variants)
    
    # With equal performance, p-value should be high (no significant difference)
    assert result["p_value"] > 0.05


def test_chi_square_test_very_different_performance(ab_test_manager):
    """Test chi-square test with very different performance (low p-value)"""
    variants = [
        {
            "creative_id": "creative_1",
            "conversions": 200,
            "impressions": 5000
        },
        {
            "creative_id": "creative_2",
            "conversions": 50,
            "impressions": 5000
        }
    ]
    
    result = ab_test_manager._chi_square_test(variants)
    
    # With very different performance, p-value should be low (significant difference)
    assert result["p_value"] < 0.05
