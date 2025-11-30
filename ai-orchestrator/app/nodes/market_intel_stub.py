"""Market Intelligence stub module node.

This module implements a stub for the Market Insights functionality.
Phase 1: Returns mock data but exercises full credit check/deduct flow.

Requirements: 需求 7 (Market Insights), 需求 12.4 (Error Recovery)
"""

import asyncio
import random
import uuid
from typing import Any

import structlog

from app.core.errors import ErrorHandler
from app.core.retry import retry_async
from app.core.state import AgentState
from app.services.mcp_client import (
    InsufficientCreditsError,
    MCPClient,
    MCPError,
)

logger = structlog.get_logger(__name__)


# Credit costs
CREDIT_COMPETITOR = 2.0
CREDIT_TRENDS = 1.5
CREDIT_STRATEGY = 3.0


def estimate_market_cost(action_type: str) -> float:
    """Estimate credit cost for market analysis action."""
    costs = {
        "analyze_competitor": CREDIT_COMPETITOR,
        "get_trends": CREDIT_TRENDS,
        "generate_strategy": CREDIT_STRATEGY,
    }
    return costs.get(action_type, 2.0)


def generate_mock_competitor_analysis() -> dict[str, Any]:
    """Generate mock competitor analysis data."""
    return {
        "competitors": [
            {
                "name": "竞品 A",
                "estimated_spend": f"${random.randint(5000, 20000)}/月",
                "main_platforms": ["Facebook", "Instagram"],
                "creative_style": "现代简约",
                "target_audience": "25-35岁女性",
                "strengths": ["素材质量高", "投放频率稳定"],
                "weaknesses": ["受众定位较窄"],
            },
            {
                "name": "竞品 B",
                "estimated_spend": f"${random.randint(3000, 15000)}/月",
                "main_platforms": ["TikTok", "Facebook"],
                "creative_style": "活力动感",
                "target_audience": "18-30岁年轻人",
                "strengths": ["视频内容丰富", "互动率高"],
                "weaknesses": ["转化率偏低"],
            },
        ],
        "market_position": "中等偏上",
        "opportunity_areas": [
            "可以尝试更多视频内容",
            "扩展到 TikTok 平台",
            "针对 35-45 岁人群的空白市场",
        ],
        "insights": [
            "🔍 竞品 A 近期增加了 Instagram Stories 投放",
            "📊 行业平均 CTR 为 1.2%，您的表现高于平均",
            "💡 建议关注竞品 B 的视频创意策略",
        ],
    }


def generate_mock_trends() -> dict[str, Any]:
    """Generate mock market trends data."""
    return {
        "trending_topics": [
            {"topic": "短视频广告", "growth": "+45%", "relevance": "高"},
            {"topic": "UGC 内容", "growth": "+32%", "relevance": "中"},
            {"topic": "AI 生成素材", "growth": "+78%", "relevance": "高"},
        ],
        "platform_trends": {
            "Facebook": {"trend": "稳定", "cpm_change": "+5%"},
            "Instagram": {"trend": "增长", "cpm_change": "+12%"},
            "TikTok": {"trend": "快速增长", "cpm_change": "-3%"},
        },
        "seasonal_insights": [
            "📅 下个月是购物旺季，建议提前准备素材",
            "🎯 节假日期间 CPM 预计上涨 20-30%",
        ],
        "recommendations": [
            "增加短视频内容投放",
            "测试 AI 生成的广告素材",
            "关注 TikTok 平台的低成本流量",
        ],
    }


def generate_mock_strategy() -> dict[str, Any]:
    """Generate mock strategy recommendations."""
    return {
        "overall_strategy": "多平台差异化投放",
        "budget_allocation": {
            "Facebook": "40%",
            "Instagram": "35%",
            "TikTok": "25%",
        },
        "creative_strategy": {
            "primary": "产品展示 + 用户评价",
            "secondary": "限时优惠 + 紧迫感",
            "testing": "AI 生成创意 A/B 测试",
        },
        "audience_strategy": {
            "core": "25-35岁，对品质有追求的消费者",
            "expansion": "35-45岁，高消费能力人群",
            "lookalike": "基于高价值客户的相似受众",
        },
        "action_items": [
            "1. 本周：生成 20 张新素材进行测试",
            "2. 下周：启动 TikTok 广告测试",
            "3. 月底：评估效果并调整预算分配",
        ],
    }


async def market_intel_stub_node(state: AgentState) -> dict[str, Any]:
    """Market Intelligence stub node with credit check.

    This stub:
    1. Estimates credit cost
    2. Checks credit via MCP
    3. Simulates analysis (1.5s delay)
    4. Deducts credit via MCP
    5. Returns mock market data

    Args:
        state: Current agent state

    Returns:
        State updates with completed results

    Requirements: 需求 7.1-7.5
    """
    log = logger.bind(
        user_id=state.get("user_id"),
        session_id=state.get("session_id"),
        module="market_intel_stub",
    )
    log.info("market_intel_stub_start")

    # Get action parameters
    pending_actions = state.get("pending_actions", [])
    market_actions = [a for a in pending_actions if a.get("module") == "market_intel"]

    if not market_actions:
        log.warning("market_intel_stub_no_actions")
        return {"completed_results": []}

    action = market_actions[0]
    action_type = action.get("type", "analyze_competitor")
    params = action.get("params", {})

    # Step 1: Estimate cost
    estimated_cost = estimate_market_cost(action_type)
    operation_id = f"market_{uuid.uuid4().hex[:12]}"

    log.info(
        "market_intel_stub_cost_estimated",
        action_type=action_type,
        estimated_cost=estimated_cost,
    )

    try:
        async with MCPClient() as mcp:
            # Step 2: Check credit with retry
            try:
                await retry_async(
                    lambda: mcp.check_credit(
                        user_id=state.get("user_id", ""),
                        estimated_credits=estimated_cost,
                        operation_type=action_type,
                    ),
                    max_retries=3,
                    context="market_intel_credit_check",
                )
                log.info("market_intel_stub_credit_check_passed")

            except InsufficientCreditsError as e:
                log.warning("market_intel_stub_insufficient_credits")
                error_state = ErrorHandler.create_node_error_state(
                    error=e,
                    node_name="market_intel_stub",
                    user_id=state.get("user_id"),
                    session_id=state.get("session_id"),
                )
                error_state["completed_results"] = [
                    {
                        "action_type": action_type,
                        "module": "market_intel",
                        "status": "error",
                        "data": {},
                        "error": error_state.get("error"),
                        "cost": 0,
                        "mock": True,
                    }
                ]
                return error_state

            except MCPError as e:
                log.error("market_intel_stub_credit_check_failed", error=str(e))
                error_state = ErrorHandler.create_node_error_state(
                    error=e,
                    node_name="market_intel_stub",
                    user_id=state.get("user_id"),
                    session_id=state.get("session_id"),
                )
                error_state["completed_results"] = [
                    {
                        "action_type": action_type,
                        "module": "market_intel",
                        "status": "error",
                        "data": {},
                        "error": error_state.get("error"),
                        "cost": 0,
                        "mock": True,
                    }
                ]
                return error_state

            # Step 3: Simulate analysis
            log.info("market_intel_stub_analyzing", action_type=action_type)
            await asyncio.sleep(1.5)

            # Step 4: Generate mock data based on action type
            if action_type == "analyze_competitor":
                mock_data = generate_mock_competitor_analysis()
            elif action_type == "get_trends":
                mock_data = generate_mock_trends()
            elif action_type == "generate_strategy":
                mock_data = generate_mock_strategy()
            else:
                mock_data = generate_mock_competitor_analysis()

            # Step 5: Deduct credit with retry
            try:
                await retry_async(
                    lambda: mcp.deduct_credit(
                        user_id=state.get("user_id", ""),
                        credits=estimated_cost,
                        operation_type=action_type,
                        operation_id=operation_id,
                    ),
                    max_retries=3,
                    context="market_intel_credit_deduct",
                )
                log.info("market_intel_stub_credit_deducted", credits=estimated_cost)

            except MCPError as e:
                log.error("market_intel_stub_credit_deduct_failed", error=str(e))

    except Exception as e:
        log.error(
            "market_intel_stub_unexpected_error",
            error=str(e),
            exc_info=True,
        )
        error_state = ErrorHandler.create_node_error_state(
            error=e,
            node_name="market_intel_stub",
            user_id=state.get("user_id"),
            session_id=state.get("session_id"),
        )
        error_state["completed_results"] = [
            {
                "action_type": action_type,
                "module": "market_intel",
                "status": "error",
                "data": {},
                "error": error_state.get("error"),
                "cost": 0,
                "mock": True,
            }
        ]
        return error_state

    # Step 6: Return result
    result = {
        "action_type": action_type,
        "module": "market_intel",
        "status": "success",
        "data": mock_data,
        "error": None,
        "cost": estimated_cost,
        "mock": True,
    }

    log.info("market_intel_stub_complete", action_type=action_type)

    return {
        "completed_results": [result],
        "credit_checked": True,
        "credit_sufficient": True,
    }
