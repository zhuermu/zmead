"""
Pydantic data models for Campaign Automation module.

These models define the data structures for campaigns, adsets, ads, rules,
A/B tests, and optimization results.

Requirements: All requirements
"""

from datetime import datetime, timezone
from typing import Literal, Optional
from pydantic import BaseModel, Field, field_serializer


class Campaign(BaseModel):
    """Campaign 数据结构
    
    Represents an advertising campaign across platforms.
    """
    
    campaign_id: str = Field(description="Campaign ID from platform")
    name: str = Field(description="Campaign name")
    objective: Literal["sales", "traffic", "awareness", "conversions"] = Field(
        description="Campaign objective"
    )
    daily_budget: float = Field(ge=0, description="Daily budget in USD")
    status: Literal["active", "paused", "deleted"] = Field(
        default="active",
        description="Campaign status"
    )
    platform: Literal["meta", "tiktok", "google"] = Field(
        description="Advertising platform"
    )
    target_roas: Optional[float] = Field(
        default=None,
        ge=0,
        description="Target ROAS for optimization"
    )
    target_cpa: Optional[float] = Field(
        default=None,
        ge=0,
        description="Target CPA for optimization"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Last update timestamp"
    )


class Targeting(BaseModel):
    """Targeting configuration for adsets"""
    
    age_min: int = Field(ge=13, le=65, description="Minimum age")
    age_max: int = Field(ge=13, le=65, description="Maximum age")
    countries: list[str] = Field(description="Target countries (ISO codes)")
    targeting_optimization: Literal["none", "lookalike"] = Field(
        default="none",
        description="Targeting optimization type"
    )


class Adset(BaseModel):
    """Adset 数据结构
    
    Represents an ad set within a campaign.
    """
    
    adset_id: str = Field(description="Adset ID from platform")
    campaign_id: str = Field(description="Parent campaign ID")
    name: str = Field(description="Adset name")
    daily_budget: float = Field(ge=0, description="Daily budget in USD")
    status: Literal["active", "paused", "deleted"] = Field(
        default="active",
        description="Adset status"
    )
    targeting: Targeting = Field(description="Targeting configuration")
    optimization_goal: Literal["value", "conversions", "clicks"] = Field(
        default="value",
        description="Optimization goal"
    )
    bid_strategy: Literal["lowest_cost", "lowest_cost_without_cap", "target_cost"] = Field(
        default="lowest_cost_without_cap",
        description="Bid strategy"
    )
    placements: Literal["automatic", "manual"] = Field(
        default="automatic",
        description="Placement strategy"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Last update timestamp"
    )


class Ad(BaseModel):
    """Ad 数据结构
    
    Represents an individual ad within an adset.
    """
    
    ad_id: str = Field(description="Ad ID from platform")
    adset_id: str = Field(description="Parent adset ID")
    creative_id: str = Field(description="Creative ID")
    name: str = Field(description="Ad name")
    ad_copy: str = Field(description="Ad copy text")
    status: Literal["active", "paused", "deleted"] = Field(
        default="active",
        description="Ad status"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Last update timestamp"
    )


class RuleCondition(BaseModel):
    """Rule condition configuration"""
    
    metric: Literal["cpa", "roas", "ctr", "spend", "conversions"] = Field(
        description="Metric to evaluate"
    )
    operator: Literal[
        "greater_than",
        "less_than",
        "equals",
        "greater_than_or_equal",
        "less_than_or_equal"
    ] = Field(description="Comparison operator")
    value: float = Field(description="Threshold value")
    time_range: str = Field(
        default="24h",
        description="Time range for evaluation (e.g., '24h', '7d')"
    )


class RuleAction(BaseModel):
    """Rule action configuration"""
    
    type: Literal[
        "pause_adset",
        "pause_campaign",
        "increase_budget",
        "decrease_budget",
        "send_notification"
    ] = Field(description="Action type")
    parameters: Optional[dict] = Field(
        default=None,
        description="Action-specific parameters"
    )


class RuleAppliesTo(BaseModel):
    """Rule application scope"""
    
    campaign_ids: Optional[list[str]] = Field(
        default=None,
        description="Campaign IDs to apply rule to"
    )
    adset_ids: Optional[list[str]] = Field(
        default=None,
        description="Adset IDs to apply rule to"
    )


class Rule(BaseModel):
    """Rule 数据结构
    
    Represents an automation rule for campaign management.
    """
    
    rule_id: str = Field(description="Rule ID")
    rule_name: str = Field(description="Rule name")
    condition: RuleCondition = Field(description="Rule condition")
    action: RuleAction = Field(description="Rule action")
    applies_to: RuleAppliesTo = Field(description="Application scope")
    check_interval: int = Field(
        default=21600,
        ge=0,
        description="Check interval in seconds (default: 6 hours)"
    )
    enabled: bool = Field(default=True, description="Whether rule is enabled")
    last_checked_at: Optional[datetime] = Field(
        default=None,
        description="Last check timestamp"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Creation timestamp"
    )


class ABTest(BaseModel):
    """A/B Test 数据结构
    
    Represents an A/B test for creative optimization.
    """
    
    test_id: str = Field(description="Test ID")
    test_name: str = Field(description="Test name")
    campaign_id: str = Field(description="Campaign ID")
    creative_ids: list[str] = Field(description="Creative IDs being tested")
    daily_budget: float = Field(ge=0, description="Total daily budget")
    test_duration_days: int = Field(ge=1, description="Test duration in days")
    start_date: datetime = Field(description="Test start date")
    end_date: datetime = Field(description="Test end date")
    status: Literal["running", "completed", "cancelled"] = Field(
        default="running",
        description="Test status"
    )
    results: Optional[dict] = Field(
        default=None,
        description="Test results (populated when completed)"
    )
    winner: Optional[str] = Field(
        default=None,
        description="Winning creative ID (if determined)"
    )


class OptimizationAction(BaseModel):
    """Single optimization action"""
    
    adset_id: str = Field(description="Target adset ID")
    action: Literal["increase_budget", "decrease_budget", "pause"] = Field(
        description="Optimization action"
    )
    old_budget: Optional[float] = Field(
        default=None,
        description="Previous budget (for budget changes)"
    )
    new_budget: Optional[float] = Field(
        default=None,
        description="New budget (for budget changes)"
    )
    reason: str = Field(description="Reason for optimization")


class OptimizationResult(BaseModel):
    """Budget optimization result
    
    Contains list of optimization actions and summary.
    """
    
    campaign_id: str = Field(description="Campaign ID")
    optimizations: list[OptimizationAction] = Field(
        description="List of optimization actions"
    )
    total_actions: int = Field(ge=0, description="Total number of actions")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Optimization timestamp"
    )


class ABTestVariant(BaseModel):
    """A/B test variant results"""
    
    creative_id: str = Field(description="Creative ID")
    spend: float = Field(ge=0, description="Total spend")
    revenue: float = Field(ge=0, description="Total revenue")
    roas: float = Field(ge=0, description="ROAS")
    ctr: float = Field(ge=0, le=1, description="CTR")
    conversions: int = Field(ge=0, description="Total conversions")
    impressions: int = Field(ge=0, description="Total impressions")
    conversion_rate: float = Field(ge=0, le=1, description="Conversion rate")
    rank: int = Field(ge=1, description="Rank by performance")


class ABTestWinner(BaseModel):
    """A/B test winner information"""
    
    creative_id: str = Field(description="Winning creative ID")
    confidence: int = Field(ge=0, le=100, description="Confidence level (%)")
    p_value: float = Field(ge=0, le=1, description="Statistical p-value")


class ABTestResult(BaseModel):
    """A/B test analysis result
    
    Contains test results, winner, and recommendations.
    """
    
    test_id: str = Field(description="Test ID")
    results: list[ABTestVariant] = Field(description="Variant results")
    winner: Optional[ABTestWinner] = Field(
        default=None,
        description="Winner information (if determined)"
    )
    recommendations: list[str] = Field(
        default_factory=list,
        description="Optimization recommendations"
    )
    message: str = Field(description="Result message")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Analysis timestamp"
    )
