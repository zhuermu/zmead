"""Context management utilities.

This module provides utilities for managing conversation context,
including reference resolution and history compression.

Requirements: 需求 5.2, 5.3, 5.4 (Context Management)
"""

import re
from typing import Any

import structlog
from langchain_core.messages import BaseMessage, SystemMessage

logger = structlog.get_logger(__name__)


# Reference patterns to detect
REFERENCE_PATTERNS = {
    # Chinese patterns
    "previous": [
        r"刚才的?",
        r"之前的?",
        r"上一个?",
        r"前面的?",
        r"那个",
        r"这个",
    ],
    # English patterns
    "previous_en": [
        r"previous",
        r"last",
        r"that",
        r"the",
        r"those",
        r"these",
    ],
    # Relative value patterns
    "relative_value": [
        r"再加\s*\$?(\d+)",
        r"增加\s*\$?(\d+)",
        r"减少\s*\$?(\d+)",
        r"多\s*\$?(\d+)",
        r"少\s*\$?(\d+)",
        r"add\s*\$?(\d+)",
        r"increase\s*\$?(\d+)",
        r"decrease\s*\$?(\d+)",
    ],
}

# Entity types that can be referenced
ENTITY_TYPES = {
    "creative": ["素材", "图片", "创意", "creative", "image"],
    "campaign": ["广告", "campaign", "投放"],
    "landing_page": ["落地页", "页面", "landing page"],
    "report": ["报表", "数据", "report"],
    "budget": ["预算", "budget"],
}


def extract_references(message: str) -> dict[str, Any]:
    """Extract context references from user message.

    Finds references like "previous", "that", "it" and identifies
    what entity type is being referenced.

    Args:
        message: User message text

    Returns:
        Dict with reference_type, entity_type, and any extracted values

    Requirements: 需求 5.2
    """
    log = logger.bind(message_preview=message[:50])

    references: dict[str, Any] = {
        "has_reference": False,
        "reference_type": None,
        "entity_type": None,
        "relative_value": None,
    }

    message_lower = message.lower()

    # Check for previous/that references
    for pattern_type, patterns in REFERENCE_PATTERNS.items():
        if pattern_type == "relative_value":
            continue  # Handle separately

        for pattern in patterns:
            if re.search(pattern, message_lower):
                references["has_reference"] = True
                references["reference_type"] = "previous"
                break

        if references["has_reference"]:
            break

    # Check for relative value references
    for pattern in REFERENCE_PATTERNS["relative_value"]:
        match = re.search(pattern, message_lower)
        if match:
            references["has_reference"] = True
            references["reference_type"] = "relative_value"
            try:
                references["relative_value"] = float(match.group(1))
            except (ValueError, IndexError):
                pass
            break

    # Identify entity type being referenced
    if references["has_reference"]:
        for entity_type, keywords in ENTITY_TYPES.items():
            for keyword in keywords:
                if keyword in message_lower:
                    references["entity_type"] = entity_type
                    break
            if references["entity_type"]:
                break

    if references["has_reference"]:
        log.info(
            "extract_references_found",
            reference_type=references["reference_type"],
            entity_type=references["entity_type"],
        )

    return references


def resolve_reference(
    reference: dict[str, Any],
    history: list[BaseMessage],
    completed_results: list[dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    """Resolve a reference to a concrete entity from history.

    Searches conversation history and completed results to find
    the entity being referenced.

    Args:
        reference: Reference info from extract_references
        history: Conversation message history
        completed_results: Results from previous actions

    Returns:
        Resolved entity data or None if not found

    Requirements: 需求 5.3
    """
    log = logger.bind(
        reference_type=reference.get("reference_type"),
        entity_type=reference.get("entity_type"),
    )

    if not reference.get("has_reference"):
        return None

    entity_type = reference.get("entity_type")

    # Search completed results first (most recent)
    if completed_results:
        for result in reversed(completed_results):
            module = result.get("module", "")
            data = result.get("data", {})

            # Match entity type to module
            if entity_type == "creative" and module == "creative":
                creative_ids = data.get("creative_ids", [])
                if creative_ids:
                    log.info("resolve_reference_found_creatives", count=len(creative_ids))
                    return {
                        "type": "creative",
                        "creative_ids": creative_ids,
                        "creatives": data.get("creatives", []),
                    }

            elif entity_type == "campaign" and module == "ad_engine":
                campaign_id = data.get("campaign_id")
                if campaign_id:
                    log.info("resolve_reference_found_campaign", campaign_id=campaign_id)
                    return {
                        "type": "campaign",
                        "campaign_id": campaign_id,
                        "campaign_data": data,
                    }

            elif entity_type == "landing_page" and module == "landing_page":
                page_id = data.get("page_id")
                if page_id:
                    log.info("resolve_reference_found_landing_page", page_id=page_id)
                    return {
                        "type": "landing_page",
                        "page_id": page_id,
                        "page_data": data,
                    }

            elif entity_type == "report" and module == "reporting":
                log.info("resolve_reference_found_report")
                return {
                    "type": "report",
                    "report_data": data,
                }

            elif entity_type == "budget":
                # Look for budget in campaign data
                budget = data.get("budget", {})
                if isinstance(budget, dict):
                    budget_value = budget.get("daily")
                elif isinstance(budget, (int, float)):
                    budget_value = budget
                else:
                    budget_value = None

                if budget_value:
                    log.info("resolve_reference_found_budget", budget=budget_value)
                    return {
                        "type": "budget",
                        "budget_value": budget_value,
                        "campaign_id": data.get("campaign_id"),
                    }

    # Search message history for mentioned entities
    # (This is a simplified implementation - could be enhanced with NER)
    for msg in reversed(history):
        if not hasattr(msg, "content"):
            continue

        content = msg.content

        # Look for IDs mentioned in messages
        if entity_type == "campaign":
            # Look for campaign IDs
            match = re.search(r"campaign[_\s]?(?:id)?[:\s]*([a-zA-Z0-9_]+)", content, re.I)
            if match:
                log.info("resolve_reference_found_in_history", campaign_id=match.group(1))
                return {
                    "type": "campaign",
                    "campaign_id": match.group(1),
                }

    log.info("resolve_reference_not_found")
    return None


def compress_history(
    messages: list[BaseMessage],
    max_rounds: int = 100,
    summary_rounds: int = 10,
) -> list[BaseMessage]:
    """Compress conversation history to fit context window.

    When conversation exceeds max_rounds, summarizes older messages
    while keeping recent ones intact.

    Args:
        messages: Full message history
        max_rounds: Maximum rounds before compression (default 100)
        summary_rounds: Number of rounds to summarize at a time

    Returns:
        Compressed message list

    Requirements: 需求 5.4
    """
    log = logger.bind(message_count=len(messages))

    # Count rounds (user-assistant pairs)
    rounds = 0
    for msg in messages:
        if hasattr(msg, "type") and msg.type == "human":
            rounds += 1

    if rounds <= max_rounds:
        log.debug("compress_history_not_needed", rounds=rounds)
        return messages

    log.info("compress_history_compressing", rounds=rounds, max_rounds=max_rounds)

    # Keep system messages
    system_messages = [m for m in messages if hasattr(m, "type") and m.type == "system"]

    # Get non-system messages
    conversation = [m for m in messages if not (hasattr(m, "type") and m.type == "system")]

    # Calculate how many messages to summarize
    # Keep the most recent (max_rounds - summary_rounds) rounds
    keep_rounds = max_rounds - summary_rounds
    keep_messages = keep_rounds * 2  # Approximate 2 messages per round

    if len(conversation) <= keep_messages:
        return messages

    # Split into old (to summarize) and recent (to keep)
    old_messages = conversation[:-keep_messages]
    recent_messages = conversation[-keep_messages:]

    # Create summary of old messages
    summary_parts = []

    # Extract key information from old messages
    topics_discussed = set()
    actions_taken = []

    for msg in old_messages:
        if not hasattr(msg, "content"):
            continue

        content = msg.content.lower()

        # Identify topics
        for entity_type, keywords in ENTITY_TYPES.items():
            for keyword in keywords:
                if keyword in content:
                    topics_discussed.add(entity_type)
                    break

        # Look for action indicators in AI messages
        if hasattr(msg, "type") and msg.type == "ai":
            if "✅" in msg.content or "完成" in msg.content:
                # Extract first line as action summary
                first_line = msg.content.split("\n")[0][:100]
                actions_taken.append(first_line)

    # Build summary
    if topics_discussed:
        summary_parts.append(f"讨论过的主题：{', '.join(topics_discussed)}")

    if actions_taken:
        summary_parts.append(f"已完成的操作：{len(actions_taken)} 项")
        # Include last few actions
        for action in actions_taken[-3:]:
            summary_parts.append(f"  - {action}")

    summary_text = "\n".join(summary_parts) if summary_parts else "（早期对话已压缩）"

    # Create summary message
    summary_message = SystemMessage(
        content=f"[对话历史摘要 - {len(old_messages)} 条消息已压缩]\n{summary_text}"
    )

    # Combine: system messages + summary + recent messages
    compressed = system_messages + [summary_message] + recent_messages

    log.info(
        "compress_history_complete",
        original_count=len(messages),
        compressed_count=len(compressed),
        summarized_count=len(old_messages),
    )

    return compressed


def get_context_window_usage(messages: list[BaseMessage]) -> dict[str, int]:
    """Calculate approximate context window usage.

    Args:
        messages: Message list

    Returns:
        Dict with message_count, estimated_tokens, rounds
    """
    total_chars = 0
    rounds = 0

    for msg in messages:
        if hasattr(msg, "content"):
            total_chars += len(msg.content)
        if hasattr(msg, "type") and msg.type == "human":
            rounds += 1

    # Rough estimate: 1 token ≈ 2 Chinese chars or 4 English chars
    # Use conservative estimate of 2 chars per token
    estimated_tokens = total_chars // 2

    return {
        "message_count": len(messages),
        "estimated_tokens": estimated_tokens,
        "rounds": rounds,
    }
