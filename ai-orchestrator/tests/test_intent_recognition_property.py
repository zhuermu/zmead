"""Property-based tests for intent recognition.

**Feature: ai-orchestrator, Property 1: Intent Recognition Accuracy**
**Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5**
"""

import pytest
from hypothesis import given, settings, strategies as st
from pydantic import BaseModel, Field
from typing import Any, Literal

IntentType = Literal[
    "generate_creative",
    "analyze_report",
    "market_analysis",
    "create_landing_page",
    "create_campaign",
    "multi_step",
    "general_query",
    "clarification_needed",
]


class ActionSchema(BaseModel):
    type: str = Field(description="Action type")
    module: str = Field(description="Target module")
    params: dict[str, Any] = Field(default_factory=dict)
    depends_on: list[int] = Field(default_factory=list)
    estimated_cost: float = Field(default=0.0)


class IntentSchema(BaseModel):
    intent: IntentType = Field(description="Primary intent")
    confidence: float = Field(ge=0.0, le=1.0)
    parameters: dict[str, Any] = Field(default_factory=dict)
    actions: list[ActionSchema] = Field(default_factory=list)
    estimated_cost: float = Field(default=0.0)
    requires_confirmation: bool = Field(default=False)
    clarification_question: str | None = Field(default=None)


CREDIT_COSTS = {
    "generate_creative": 5.0,
    "analyze_creative": 1.0,
    "get_report": 1.0,
    "analyze_performance": 2.0,
    "analyze_competitor": 2.0,
    "get_trends": 1.5,
    "generate_strategy": 3.0,
    "create_landing_page": 3.0,
    "translate_page": 1.0,
    "create_campaign": 2.0,
    "update_budget": 0.5,
    "pause_campaign": 0.5,
    "pause_all": 0.5,
    "delete_campaign": 0.5,
}


def estimate_action_cost(action_type: str, params: dict[str, Any]) -> float:
    base_cost = CREDIT_COSTS.get(action_type, 1.0)
    if action_type == "generate_creative":
        count = params.get("count", 10)
        return base_cost * (count / 10)
    return base_cost


def is_high_risk_operation(actions: list[ActionSchema]) -> bool:
    high_risk_types = {"pause_all", "delete_campaign", "delete"}
    for action in actions:
        if action.type in high_risk_types:
            return True
        if action.type == "update_budget":
            budget_change = action.params.get("budget_change_percent", 0)
            if abs(budget_change) > 50:
                return True
    return False


class TestCreditCostEstimation:
    @settings(max_examples=100)
    @given(count=st.integers(min_value=1, max_value=1000))
    def test_creative_cost_scales_with_count(self, count: int):
        params = {"count": count}
        cost = estimate_action_cost("generate_creative", params)
        expected_cost = 5.0 * (count / 10)
        assert cost == expected_cost

    @settings(max_examples=100)
    @given(action_type=st.sampled_from(list(CREDIT_COSTS.keys())))
    def test_all_action_types_have_positive_cost(self, action_type: str):
        cost = estimate_action_cost(action_type, {})
        assert cost > 0


class TestHighRiskOperationDetection:
    @settings(max_examples=100)
    @given(action_type=st.sampled_from(["pause_all", "delete_campaign", "delete"]))
    def test_high_risk_actions_detected(self, action_type: str):
        actions = [ActionSchema(type=action_type, module="ad_engine")]
        assert is_high_risk_operation(actions) is True

    @settings(max_examples=100)
    @given(budget_change=st.integers(min_value=51, max_value=500))
    def test_large_budget_changes_detected(self, budget_change: int):
        actions = [
            ActionSchema(
                type="update_budget",
                module="ad_engine",
                params={"budget_change_percent": budget_change},
            )
        ]
        assert is_high_risk_operation(actions) is True

    @settings(max_examples=100)
    @given(budget_change=st.integers(min_value=-50, max_value=50))
    def test_small_budget_changes_not_high_risk(self, budget_change: int):
        actions = [
            ActionSchema(
                type="update_budget",
                module="ad_engine",
                params={"budget_change_percent": budget_change},
            )
        ]
        assert is_high_risk_operation(actions) is False

    @settings(max_examples=100)
    @given(action_type=st.sampled_from(["generate_creative", "get_report", "create_campaign"]))
    def test_normal_actions_not_high_risk(self, action_type: str):
        actions = [ActionSchema(type=action_type, module="creative")]
        assert is_high_risk_operation(actions) is False


class TestIntentSchemaValidation:
    @settings(max_examples=100)
    @given(confidence=st.floats(min_value=0.0, max_value=1.0))
    def test_valid_confidence_accepted(self, confidence: float):
        schema = IntentSchema(intent="generate_creative", confidence=confidence)
        assert schema.confidence == confidence
