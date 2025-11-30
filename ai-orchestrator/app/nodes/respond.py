"""Response generator node.

This module implements the respond_node that generates user-friendly
responses based on execution results.

Requirements: 需求 1.2 (Response), 需求 14.3 (Explanations), 需求 12.4 (Error Recovery)
"""

import json
from typing import Any

import structlog
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from app.core.config import get_settings
from app.core.state import AgentState
from app.prompts.response_generation import (
    RESPONSE_GENERATION_SYSTEM_PROMPT,
    RESPONSE_GENERATION_USER_PROMPT,
    RESPONSE_TEMPLATES,
    format_creative_list,
    format_insights,
)

logger = structlog.get_logger(__name__)

# Global LLM instance for streaming (lazy initialized)
_streaming_llm: ChatGoogleGenerativeAI | None = None


def get_streaming_llm() -> ChatGoogleGenerativeAI:
    """Get or create the streaming LLM instance."""
    global _streaming_llm
    if _streaming_llm is None:
        settings = get_settings()
        _streaming_llm = ChatGoogleGenerativeAI(
            model=settings.gemini_model_fast,
            google_api_key=settings.gemini_api_key,
            temperature=0.3,
            streaming=True,  # Enable streaming
        )
    return _streaming_llm


def generate_insufficient_credit_response(state: AgentState) -> str:
    """Generate response for insufficient credits.

    Args:
        state: Current agent state

    Returns:
        Formatted response string
    """
    error = state.get("error", {})
    details = error.get("details", {})

    required = details.get("required", "未知")
    available = details.get("available", "未知")

    return RESPONSE_TEMPLATES["insufficient_credits"].format(
        required=required,
        available=available,
    )


def generate_error_response(state: AgentState) -> str:
    """Generate response for errors.

    Args:
        state: Current agent state

    Returns:
        Formatted response string
    """
    error = state.get("error", {})
    error_type = error.get("type", "UNKNOWN_ERROR")
    message = error.get("message", "发生未知错误")

    # Map error types to suggestions
    suggestions = {
        "MCP_CONNECTION_FAILED": "请检查网络连接后重试",
        "AI_MODEL_ERROR": "请稍后重试，或尝试简化您的请求",
        "INSUFFICIENT_CREDITS": "请充值后继续使用",
        "TIMEOUT": "请稍后重试",
        "UNKNOWN_ERROR": "如果问题持续，请联系客服",
    }

    suggestion = suggestions.get(error_type, suggestions["UNKNOWN_ERROR"])

    return RESPONSE_TEMPLATES["error_generic"].format(
        message=message,
        suggestion=suggestion,
    )


def format_result_for_prompt(results: list[dict[str, Any]]) -> str:
    """Format execution results for the LLM prompt.

    Args:
        results: List of action results

    Returns:
        JSON string of results
    """
    # Simplify results for the prompt
    simplified = []
    for result in results:
        simplified.append(
            {
                "action": result.get("action_type"),
                "module": result.get("module"),
                "status": result.get("status"),
                "data": result.get("data", {}),
                "error": result.get("error"),
                "mock": result.get("mock", False),
            }
        )

    return json.dumps(simplified, ensure_ascii=False, indent=2)


async def respond_node(state: AgentState) -> dict[str, Any]:
    """Response generator node.

    This node:
    1. Checks for errors and generates appropriate responses
    2. Formats successful results into user-friendly messages
    3. Uses Gemini 2.5 Flash for fast response generation
    4. Includes next step suggestions

    Args:
        state: Current agent state

    Returns:
        State updates with response message

    Requirements: 需求 1.2, 14.3
    """
    log = logger.bind(
        user_id=state.get("user_id"),
        session_id=state.get("session_id"),
    )
    log.info("respond_node_start")

    # Check for errors first
    error = state.get("error")
    if error:
        error_type = error.get("type", "")

        if error_type == "INSUFFICIENT_CREDITS":
            response = generate_insufficient_credit_response(state)
            log.info("respond_node_insufficient_credits")
        else:
            response = generate_error_response(state)
            log.info("respond_node_error", error_type=error_type)

        return {"messages": [AIMessage(content=response)]}

    # Get completed results
    results = state.get("completed_results", [])

    if not results:
        # No results - might be a general query or clarification
        intent = state.get("current_intent")

        if intent == "clarification_needed":
            # Clarification message should already be in messages
            return {}

        # Use streaming LLM for general queries to enable token streaming
        try:
            llm = get_streaming_llm()

            # Get user's message for context
            messages = state.get("messages", [])
            user_message = ""
            for msg in reversed(messages):
                if hasattr(msg, "type") and msg.type == "human":
                    user_message = msg.content
                    break

            # Create a conversational prompt
            system_prompt = """你是 AAE 智能广告助手。你可以帮助用户：
- 🎨 生成广告素材
- 📊 查看投放数据和报表
- 🔍 分析市场趋势和竞品
- 📄 创建落地页
- 📢 管理广告投放

请用友好、专业的语气回复用户。保持简洁，每个回复不超过100字。"""

            prompt_messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_message or "你好"),
            ]

            response = await llm.ainvoke(prompt_messages)
            log.info("respond_node_general_query_streaming")
            return {"messages": [response]}

        except Exception as e:
            log.error("respond_node_general_query_error", error=str(e))
            # Fallback to static response
            response = (
                "你好！我是你的广告投放助手。我可以帮你：\n\n"
                "🎨 生成广告素材\n"
                "📊 查看投放数据\n"
                "🔍 分析市场趋势\n"
                "📄 创建落地页\n"
                "📢 管理广告投放\n\n"
                "有什么我可以帮你的吗？"
            )
            return {"messages": [AIMessage(content=response)]}

    # Check if any result has an error
    error_results = [r for r in results if r.get("status") == "error"]
    if error_results:
        error_info = error_results[0].get("error", {})
        if error_info.get("type") == "INSUFFICIENT_CREDITS":
            response = generate_insufficient_credit_response(
                {
                    "error": error_info,
                }
            )
            return {"messages": [AIMessage(content=response)]}

    # Get user's original request
    messages = state.get("messages", [])
    user_request = ""
    for msg in reversed(messages):
        if hasattr(msg, "type") and msg.type == "human":
            user_request = msg.content
            break

    # Check if all results are mock
    is_mock = all(r.get("mock", False) for r in results)

    # Use streaming LLM for real token streaming
    try:
        llm = get_streaming_llm()

        prompt_messages = [
            SystemMessage(content=RESPONSE_GENERATION_SYSTEM_PROMPT),
            HumanMessage(
                content=RESPONSE_GENERATION_USER_PROMPT.format(
                    results=format_result_for_prompt(results),
                    user_request=user_request,
                    has_error="否",
                    error_message="无",
                    is_mock="是" if is_mock else "否",
                )
            ),
        ]

        # Use ainvoke - LangGraph's astream_events will capture the streaming tokens
        response = await llm.ainvoke(prompt_messages)

        log.info(
            "respond_node_llm_complete",
            response_length=len(response.content) if response.content else 0,
        )

        return {"messages": [response]}

    except Exception as e:
        log.error("respond_node_llm_error", error=str(e), exc_info=True)

        # Fallback to template-based response
        response = generate_fallback_response(results, is_mock)
        return {"messages": [AIMessage(content=response)]}


def generate_fallback_response(
    results: list[dict[str, Any]],
    is_mock: bool,
) -> str:
    """Generate fallback response when LLM fails.

    Args:
        results: List of action results
        is_mock: Whether results are mock data

    Returns:
        Formatted response string
    """
    if not results:
        return "✅ 操作完成！"

    result = results[0]
    module = result.get("module", "")
    data = result.get("data", {})

    # Use message from data if available
    if "message" in data:
        return data["message"]

    # Generate based on module
    if module == "creative":
        creatives = data.get("creatives", [])
        count = len(creatives)

        if is_mock:
            return RESPONSE_TEMPLATES["creative_success_mock"].format(
                count=count,
                creative_list=format_creative_list(creatives),
            )
        else:
            return RESPONSE_TEMPLATES["creative_success"].format(
                count=count,
                creative_list=format_creative_list(creatives),
            )

    elif module == "reporting":
        summary = data.get("summary", {})
        insights = data.get("insights", [])

        return RESPONSE_TEMPLATES["report_success"].format(
            date_range=data.get("date_range", "最近 7 天"),
            spend=summary.get("spend", 0),
            impressions=f"{summary.get('impressions', 0):,}",
            clicks=f"{summary.get('clicks', 0):,}",
            ctr=summary.get("ctr", 0),
            roas=summary.get("roas", 0),
            insights=format_insights(insights),
            suggestion="继续保持当前策略" if summary.get("roas", 0) > 2 else "建议优化素材和受众",
        )

    elif module == "ad_engine":
        campaign_id = data.get("campaign_id", "")
        if campaign_id:
            return RESPONSE_TEMPLATES["campaign_created"].format(
                campaign_id=campaign_id,
                budget=data.get("budget", {}).get("daily", 100),
                target_roas=data.get("targeting", {}).get("target_roas", 3.0),
                status="🟢 投放中",
            )

    # Default response
    response = "✅ 操作完成！"
    if is_mock:
        response += "（模拟数据）"

    return response
