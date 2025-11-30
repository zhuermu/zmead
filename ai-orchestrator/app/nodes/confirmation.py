"""Human confirmation node.

This module implements the human_confirmation_node that handles
high-risk operations requiring user confirmation.

Requirements: 需求 14.5 (Safety Confirmation)
"""

from typing import Any

import structlog
from langchain_core.messages import AIMessage

from app.core.state import AgentState

logger = structlog.get_logger(__name__)


# High-risk action types that require confirmation
HIGH_RISK_ACTIONS = {
    "pause_all",
    "delete_campaign",
    "delete",
}

# Budget change threshold (percentage) that requires confirmation
BUDGET_CHANGE_THRESHOLD = 50


def is_high_risk_operation(actions: list[dict[str, Any]]) -> bool:
    """Check if any action is high-risk and requires confirmation.

    High-risk operations:
    - pause_all: Pausing all campaigns
    - delete_campaign: Deleting campaigns
    - budget_change > 50%

    Args:
        actions: List of pending actions

    Returns:
        True if any action is high-risk
    """
    for action in actions:
        action_type = action.get("type", "")

        # Check for explicitly high-risk actions
        if action_type in HIGH_RISK_ACTIONS:
            return True

        # Check for large budget changes
        if action_type == "update_budget":
            params = action.get("params", {})
            budget_change = params.get("budget_change_percent", 0)
            if abs(budget_change) > BUDGET_CHANGE_THRESHOLD:
                return True

    return False


def get_operation_description(actions: list[dict[str, Any]]) -> str:
    """Get human-readable description of the operation.

    Args:
        actions: List of pending actions

    Returns:
        Description string
    """
    if not actions:
        return "未知操作"

    action = actions[0]
    action_type = action.get("type", "")
    params = action.get("params", {})

    descriptions = {
        "pause_all": "暂停所有广告",
        "delete_campaign": f"删除广告 {params.get('campaign_id', '')}",
        "delete": f"删除 {params.get('target', '资源')}",
        "update_budget": f"修改预算到 ${params.get('budget', 0)}",
    }

    return descriptions.get(action_type, f"执行 {action_type}")


def get_operation_impact(actions: list[dict[str, Any]]) -> str:
    """Get description of the operation's impact.

    Args:
        actions: List of pending actions

    Returns:
        Impact description string
    """
    if not actions:
        return "- 影响未知"

    action = actions[0]
    action_type = action.get("type", "")
    params = action.get("params", {})

    impacts = {
        "pause_all": [
            "- 所有正在投放的广告将立即暂停",
            "- 广告将停止展示和消耗预算",
            "- 可能影响正在进行的营销活动",
        ],
        "delete_campaign": [
            "- 广告将被永久删除",
            "- 相关数据将无法恢复",
            "- 历史报表数据仍会保留",
        ],
        "delete": [
            "- 资源将被永久删除",
            "- 此操作无法撤销",
        ],
        "update_budget": [
            f"- 预算将从当前值修改为 ${params.get('budget', 0)}",
            "- 变化幅度较大，请确认",
            "- 修改将立即生效",
        ],
    }

    impact_list = impacts.get(action_type, ["- 操作将立即执行"])
    return "\n".join(impact_list)


def get_expected_result(actions: list[dict[str, Any]]) -> str:
    """Get description of expected result.

    Args:
        actions: List of pending actions

    Returns:
        Expected result description
    """
    if not actions:
        return "操作完成"

    action = actions[0]
    action_type = action.get("type", "")

    results = {
        "pause_all": "所有广告状态变为「已暂停」",
        "delete_campaign": "广告从系统中移除",
        "delete": "资源从系统中移除",
        "update_budget": "新预算立即生效",
    }

    return results.get(action_type, "操作完成")


def generate_confirmation_message(
    actions: list[dict[str, Any]],
) -> str:
    """Generate confirmation message for high-risk operation.

    Args:
        actions: List of pending actions

    Returns:
        Formatted confirmation message
    """
    operation = get_operation_description(actions)
    impact = get_operation_impact(actions)
    expected_result = get_expected_result(actions)

    message = f"""⚠️ **请确认操作**

即将执行：**{operation}**

**影响范围**：
{impact}

**预计结果**：
{expected_result}

---
回复「确认」继续执行，或「取消」放弃操作。"""

    return message


async def human_confirmation_node(state: AgentState) -> dict[str, Any]:
    """Human confirmation node for high-risk operations.

    This node:
    1. Detects high-risk operations
    2. Generates confirmation message with operation details
    3. Sets requires_confirmation flag
    4. Returns END to wait for user input

    The graph will resume when user confirms/cancels via state update.

    Args:
        state: Current agent state

    Returns:
        State updates with confirmation message and flag

    Requirements: 需求 14.5.1, 14.5.2, 14.5.3
    """
    log = logger.bind(
        user_id=state.get("user_id"),
        session_id=state.get("session_id"),
    )
    log.info("human_confirmation_node_start")

    # Get pending actions
    pending_actions = state.get("pending_actions", [])

    if not pending_actions:
        log.warning("human_confirmation_no_actions")
        return {}

    # Check if already confirmed
    if state.get("user_confirmed") is True:
        log.info("human_confirmation_already_confirmed")
        return {"requires_confirmation": False}

    # Check if user cancelled
    if state.get("user_confirmed") is False:
        log.info("human_confirmation_cancelled")
        return {
            "requires_confirmation": False,
            "pending_actions": [],  # Clear pending actions
            "messages": [
                AIMessage(content="✅ 操作已取消\n\n没有进行任何更改。有其他需要帮助的吗？")
            ],
        }

    # Generate confirmation message
    confirmation_message = generate_confirmation_message(pending_actions)

    log.info(
        "human_confirmation_waiting",
        action_types=[a.get("type") for a in pending_actions],
    )

    return {
        "requires_confirmation": True,
        "user_confirmed": None,  # Waiting for confirmation
        "confirmation_message": confirmation_message,
        "messages": [AIMessage(content=confirmation_message)],
    }


def check_confirmation_response(user_message: str) -> bool | None:
    """Check if user message is a confirmation or cancellation.

    Args:
        user_message: User's response message

    Returns:
        True if confirmed, False if cancelled, None if unclear
    """
    message_lower = user_message.lower().strip()

    # Confirmation keywords
    confirm_keywords = {
        "确认",
        "确定",
        "是",
        "好",
        "ok",
        "yes",
        "confirm",
        "继续",
        "执行",
        "同意",
        "可以",
        "行",
    }

    # Cancellation keywords
    cancel_keywords = {
        "取消",
        "不",
        "否",
        "no",
        "cancel",
        "算了",
        "放弃",
        "停止",
        "不要",
        "别",
    }

    for keyword in confirm_keywords:
        if keyword in message_lower:
            return True

    for keyword in cancel_keywords:
        if keyword in message_lower:
            return False

    return None
