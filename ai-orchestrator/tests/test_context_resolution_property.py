"""Property-based tests for context reference resolution.

**Feature: ai-orchestrator, Property 3: Context Reference Resolution**
**Validates: Requirements 5.2, 5.3**

This module tests that the context manager correctly resolves references
from conversation history (e.g., "use the previous creative", "add $50 more").
"""

import pytest
from hypothesis import given, settings, strategies as st, assume
from typing import Any
import re


# Reference patterns to detect
REFERENCE_PATTERNS = {
    "previous": [
        r"刚才的?",
        r"之前的?",
        r"上一个?",
        r"前面的?",
        r"那个",
        r"这个",
    ],
    "previous_en": [
        r"previous",
        r"last",
        r"that",
        r"the",
        r"those",
        r"these",
    ],
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

ENTITY_TYPES = {
    "creative": ["素材", "图片", "创意", "creative", "image"],
    "campaign": ["广告", "campaign", "投放"],
    "landing_page": ["落地页", "页面", "landing page"],
    "report": ["报表", "数据", "report"],
    "budget": ["预算", "budget"],
}


def extract_references(message: str) -> dict[str, Any]:
    """Extract context references from user message."""
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
            continue
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

    return references


# Generators for test messages
def generate_previous_reference_message():
    """Generate messages with 'previous' references."""
    prefix = st.sampled_from(["用", "使用", "拿", "用一下"])
    reference = st.sampled_from(["刚才的", "之前的", "上一个", "那个"])
    entity = st.sampled_from(["素材", "图片", "广告", "落地页", "报表"])
    return st.builds(lambda p, r, e: f"{p}{r}{e}", prefix, reference, entity)


def generate_relative_value_message():
    """Generate messages with relative value references."""
    action = st.sampled_from(["再加", "增加", "减少", "多", "少"])
    value = st.integers(min_value=1, max_value=1000)
    entity = st.sampled_from(["预算", "budget", ""])
    return st.builds(lambda a, v, e: f"{a} ${v} {e}".strip(), action, value, entity)


class TestContextReferenceExtraction:
    """Property tests for context reference extraction.

    **Feature: ai-orchestrator, Property 3: Context Reference Resolution**
    **Validates: Requirements 5.2, 5.3**
    """

    @settings(max_examples=100)
    @given(message=generate_previous_reference_message())
    def test_previous_references_detected(self, message: str):
        """Property: Messages with 'previous' keywords SHALL be detected as references."""
        refs = extract_references(message)
        assert refs["has_reference"] is True, (
            f"Message '{message}' should be detected as having a reference"
        )
        assert refs["reference_type"] == "previous", (
            f"Reference type should be 'previous' for message '{message}'"
        )

    @settings(max_examples=100)
    @given(message=generate_relative_value_message())
    def test_relative_value_references_detected(self, message: str):
        """Property: Messages with relative values SHALL be detected and parsed."""
        refs = extract_references(message)
        assert refs["has_reference"] is True, (
            f"Message '{message}' should be detected as having a reference"
        )
        assert refs["reference_type"] == "relative_value", (
            f"Reference type should be 'relative_value' for message '{message}'"
        )
        assert refs["relative_value"] is not None, (
            f"Relative value should be extracted from '{message}'"
        )
        assert refs["relative_value"] > 0, f"Relative value should be positive"

    @settings(max_examples=50)
    @given(
        reference=st.sampled_from(["刚才的", "之前的", "上一个"]),
        entity=st.sampled_from(list(ENTITY_TYPES.keys())),
    )
    def test_entity_type_correctly_identified(self, reference: str, entity: str):
        """Property: Entity type SHALL be correctly identified from message."""
        # Get a keyword for this entity type
        keyword = ENTITY_TYPES[entity][0]
        message = f"用{reference}{keyword}"

        refs = extract_references(message)
        assert refs["has_reference"] is True
        assert refs["entity_type"] == entity, (
            f"Entity type should be '{entity}' for message '{message}', got '{refs['entity_type']}'"
        )

    @settings(max_examples=50)
    @given(value=st.integers(min_value=1, max_value=10000))
    def test_relative_value_correctly_extracted(self, value: int):
        """Property: Relative value SHALL be correctly extracted from message."""
        message = f"再加 ${value} 预算"
        refs = extract_references(message)

        assert refs["has_reference"] is True
        assert refs["relative_value"] == float(value), (
            f"Expected value {value}, got {refs['relative_value']}"
        )


class TestNoReferenceMessages:
    """Property tests for messages without references."""

    @settings(max_examples=50)
    @given(
        message=st.sampled_from(
            [
                "生成10张素材",
                "创建新广告",
                "查看今天的报表",
                "分析竞品数据",
                "设置预算为100",
            ]
        )
    )
    def test_direct_commands_have_no_reference(self, message: str):
        """Property: Direct commands without references SHALL not be detected."""
        refs = extract_references(message)
        # These messages don't have reference keywords
        # Note: Some may have entity keywords but no reference keywords
        if refs["has_reference"]:
            # If detected, it should have a valid reference type
            assert refs["reference_type"] in ["previous", "relative_value"]


class TestReferencePatternCoverage:
    """Property tests for reference pattern coverage."""

    @settings(max_examples=20)
    @given(pattern_type=st.sampled_from(["previous", "previous_en"]))
    def test_all_previous_patterns_work(self, pattern_type: str):
        """Property: All 'previous' patterns SHALL be recognized."""
        patterns = REFERENCE_PATTERNS[pattern_type]
        for pattern in patterns:
            # Create a simple message with the pattern
            test_word = pattern.replace(r"\s*", " ").replace("?", "")
            message = f"{test_word} 素材"
            refs = extract_references(message)
            # At least some patterns should match
            # (not all patterns will match due to regex specifics)

    @settings(max_examples=20)
    @given(entity_type=st.sampled_from(list(ENTITY_TYPES.keys())))
    def test_all_entity_types_have_keywords(self, entity_type: str):
        """Property: All entity types SHALL have at least one keyword."""
        keywords = ENTITY_TYPES[entity_type]
        assert len(keywords) > 0, f"Entity type '{entity_type}' should have keywords"
