"""Prompt templates for AI Orchestrator.

This package contains prompt templates for:
- Intent recognition
- Response generation
"""

from app.prompts.intent_recognition import (
    INTENT_EXAMPLES,
    INTENT_RECOGNITION_SYSTEM_PROMPT,
    INTENT_RECOGNITION_USER_PROMPT,
    format_conversation_history,
)
from app.prompts.response_generation import (
    RESPONSE_GENERATION_SYSTEM_PROMPT,
    RESPONSE_GENERATION_USER_PROMPT,
    RESPONSE_TEMPLATES,
    format_creative_list,
    format_insights,
    get_response_template,
)

__all__ = [
    # Intent recognition
    "INTENT_RECOGNITION_SYSTEM_PROMPT",
    "INTENT_RECOGNITION_USER_PROMPT",
    "INTENT_EXAMPLES",
    "format_conversation_history",
    # Response generation
    "RESPONSE_GENERATION_SYSTEM_PROMPT",
    "RESPONSE_GENERATION_USER_PROMPT",
    "RESPONSE_TEMPLATES",
    "get_response_template",
    "format_creative_list",
    "format_insights",
]
