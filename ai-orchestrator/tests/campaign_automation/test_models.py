"""
Unit tests for Campaign Automation data models.

Tests Pydantic model validation and serialization.
"""

import pytest
from datetime import datetime, timedelta
from pydantic import ValidationError

from app.modules.campaign_automation.models import (
    Campaign,
    Adset,
    Ad,
    Targeting,
    Rule,
    RuleCondition,
    RuleAction,
    RuleAppliesTo,
    ABTest,
    OptimizationAction,
    OptimizationResult,
    ABTestVariant,
    ABTestWinner,
    ABTestResult,
)


def test_campaign_model_valid():
    """Test Campaign model with valid data"""
    campaign = Campaign(
        campaign_id="campaign_123",
        name="Test Campaign",
        objective="sales",
        daily_budget=100.0,
        platform="meta",
        target_roas=3.0,
    )
    
    assert campaign.campaign_id == "campaign_123"
    assert campaign.name == "Test Campaign"
    assert campaign.objective == "sales"
    assert campaign.daily_budget == 100.0
    assert campaign.platform == "meta"
    assert campaign.target_roas == 3.0
    assert campaign.status == "active"  # default


def test_campaign_model_invalid_objective():
    """Test Campaign model rejects invalid objective"""
    with pytest.raises(ValidationError):
        Campaign(
            campaign_id="campaign_123",
            name="Test Campaign",
            objective="invalid_objective",
            daily_budget=100.0,
            platform="meta",
        )


def test_campaign_model_negative_budget():
    """Test Campaign model rejects negative budget"""
    with pytest.raises(ValidationError):
        Campaign(
            campaign_id="campaign_123",
            name="Test Campaign",
            objective="sales",
            daily_budget=-10.0,
            platform="meta",
        )


def test_targeting_model_valid():
    """Test Targeting model with valid data"""
    targeting = Targeting(
        age_min=18,
        age_max=35,
        countries=["US", "CA"],
        targeting_optimization="none",
    )
    
    assert targeting.age_min == 18
    assert targeting.age_max == 35
    assert targeting.countries == ["US", "CA"]
    assert targeting.targeting_optimization == "none"


def test_targeting_model_invalid_age():
    """Test Targeting model rejects invalid age range"""
    with pytest.raises(ValidationError):
        Targeting(
            age_min=10,  # Too young
            age_max=35,
            countries=["US"],
        )


def test_adset_model_valid():
    """Test Adset model with valid data"""
    adset = Adset(
        adset_id="adset_123",
        campaign_id="campaign_123",
        name="Test Adset",
        daily_budget=33.33,
        targeting=Targeting(
            age_min=18,
            age_max=35,
            countries=["US"],
        ),
    )
    
    assert adset.adset_id == "adset_123"
    assert adset.campaign_id == "campaign_123"
    assert adset.daily_budget == 33.33
    assert adset.optimization_goal == "value"  # default
    assert adset.bid_strategy == "lowest_cost_without_cap"  # default
    assert adset.placements == "automatic"  # default


def test_ad_model_valid():
    """Test Ad model with valid data"""
    ad = Ad(
        ad_id="ad_123",
        adset_id="adset_123",
        creative_id="creative_123",
        name="Test Ad",
        ad_copy="限时优惠！立即购买",
    )
    
    assert ad.ad_id == "ad_123"
    assert ad.adset_id == "adset_123"
    assert ad.creative_id == "creative_123"
    assert ad.ad_copy == "限时优惠！立即购买"
    assert ad.status == "active"  # default


def test_rule_condition_model_valid():
    """Test RuleCondition model with valid data"""
    condition = RuleCondition(
        metric="cpa",
        operator="greater_than",
        value=50.0,
        time_range="24h",
    )
    
    assert condition.metric == "cpa"
    assert condition.operator == "greater_than"
    assert condition.value == 50.0
    assert condition.time_range == "24h"


def test_rule_action_model_valid():
    """Test RuleAction model with valid data"""
    action = RuleAction(
        type="pause_adset",
        parameters={"reason": "High CPA"},
    )
    
    assert action.type == "pause_adset"
    assert action.parameters == {"reason": "High CPA"}


def test_rule_model_valid():
    """Test Rule model with valid data"""
    rule = Rule(
        rule_id="rule_123",
        rule_name="Auto Pause High CPA",
        condition=RuleCondition(
            metric="cpa",
            operator="greater_than",
            value=50.0,
            time_range="24h",
        ),
        action=RuleAction(type="pause_adset"),
        applies_to=RuleAppliesTo(campaign_ids=["campaign_123"]),
    )
    
    assert rule.rule_id == "rule_123"
    assert rule.rule_name == "Auto Pause High CPA"
    assert rule.enabled is True  # default
    assert rule.check_interval == 21600  # default (6 hours)


def test_ab_test_model_valid():
    """Test ABTest model with valid data"""
    from datetime import timezone
    start_date = datetime.now(timezone.utc)
    end_date = start_date + timedelta(days=3)
    
    ab_test = ABTest(
        test_id="test_123",
        test_name="Creative Test",
        campaign_id="campaign_123",
        creative_ids=["creative_1", "creative_2", "creative_3"],
        daily_budget=90.0,
        test_duration_days=3,
        start_date=start_date,
        end_date=end_date,
    )
    
    assert ab_test.test_id == "test_123"
    assert ab_test.test_name == "Creative Test"
    assert len(ab_test.creative_ids) == 3
    assert ab_test.daily_budget == 90.0
    assert ab_test.status == "running"  # default


def test_optimization_action_model_valid():
    """Test OptimizationAction model with valid data"""
    action = OptimizationAction(
        adset_id="adset_123",
        action="increase_budget",
        old_budget=30.0,
        new_budget=36.0,
        reason="ROAS 3.5 超过目标，表现优秀",
    )
    
    assert action.adset_id == "adset_123"
    assert action.action == "increase_budget"
    assert action.old_budget == 30.0
    assert action.new_budget == 36.0


def test_optimization_result_model_valid():
    """Test OptimizationResult model with valid data"""
    result = OptimizationResult(
        campaign_id="campaign_123",
        optimizations=[
            OptimizationAction(
                adset_id="adset_1",
                action="increase_budget",
                old_budget=30.0,
                new_budget=36.0,
                reason="ROAS超标",
            ),
            OptimizationAction(
                adset_id="adset_2",
                action="pause",
                reason="连续3天无转化",
            ),
        ],
        total_actions=2,
    )
    
    assert result.campaign_id == "campaign_123"
    assert len(result.optimizations) == 2
    assert result.total_actions == 2


def test_ab_test_variant_model_valid():
    """Test ABTestVariant model with valid data"""
    variant = ABTestVariant(
        creative_id="creative_1",
        spend=90.0,
        revenue=315.0,
        roas=3.5,
        ctr=0.028,
        conversions=150,
        impressions=5000,
        conversion_rate=0.03,
        rank=1,
    )
    
    assert variant.creative_id == "creative_1"
    assert variant.spend == 90.0
    assert variant.revenue == 315.0
    assert variant.roas == 3.5
    assert variant.rank == 1


def test_ab_test_winner_model_valid():
    """Test ABTestWinner model with valid data"""
    winner = ABTestWinner(
        creative_id="creative_1",
        confidence=95,
        p_value=0.03,
    )
    
    assert winner.creative_id == "creative_1"
    assert winner.confidence == 95
    assert winner.p_value == 0.03


def test_ab_test_result_model_valid():
    """Test ABTestResult model with valid data"""
    result = ABTestResult(
        test_id="test_123",
        results=[
            ABTestVariant(
                creative_id="creative_1",
                spend=90.0,
                revenue=315.0,
                roas=3.5,
                ctr=0.028,
                conversions=150,
                impressions=5000,
                conversion_rate=0.03,
                rank=1,
            ),
        ],
        winner=ABTestWinner(
            creative_id="creative_1",
            confidence=95,
            p_value=0.03,
        ),
        recommendations=["暂停 creative_3（表现最差）"],
        message="测试完成，已识别获胜者",
    )
    
    assert result.test_id == "test_123"
    assert len(result.results) == 1
    assert result.winner is not None
    assert result.winner.creative_id == "creative_1"
    assert len(result.recommendations) == 1


def test_model_serialization():
    """Test model serialization to dict"""
    campaign = Campaign(
        campaign_id="campaign_123",
        name="Test Campaign",
        objective="sales",
        daily_budget=100.0,
        platform="meta",
    )
    
    data = campaign.model_dump()
    
    assert isinstance(data, dict)
    assert data["campaign_id"] == "campaign_123"
    assert data["name"] == "Test Campaign"
    assert data["objective"] == "sales"
    assert data["daily_budget"] == 100.0
    assert data["platform"] == "meta"


def test_model_json_serialization():
    """Test model JSON serialization"""
    campaign = Campaign(
        campaign_id="campaign_123",
        name="Test Campaign",
        objective="sales",
        daily_budget=100.0,
        platform="meta",
    )
    
    json_data = campaign.model_dump(mode="json")
    
    assert isinstance(json_data, dict)
    assert isinstance(json_data["created_at"], str)  # datetime serialized to string
    assert isinstance(json_data["updated_at"], str)
