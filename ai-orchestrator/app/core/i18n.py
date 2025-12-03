"""Internationalization utilities for AI Orchestrator.

Provides translation support for user-facing messages.
"""

from typing import Literal

Language = Literal["en", "zh"]

# Translation dictionary
TRANSLATIONS = {
    "user_input_required": {
        "en": "Your input is required",
        "zh": "需要您的输入",
    },
    "processing_error": {
        "en": "Sorry, an error occurred while processing your request: {error}",
        "zh": "抱歉，处理请求时出错：{error}",
    },
    "thinking": {
        "en": "Thinking...",
        "zh": "正在思考...",
    },
    "unknown_error": {
        "en": "An unknown error occurred",
        "zh": "发生未知错误",
    },
    "operation_cancelled": {
        "en": "Operation cancelled",
        "zh": "操作已取消",
    },
    "tool_executing": {
        "en": "Executing {tool}...",
        "zh": "正在执行 {tool}...",
    },
}


def get_message(key: str, language: Language = "en", **kwargs) -> str:
    """Get translated message.
    
    Args:
        key: Translation key
        language: Target language (en or zh)
        **kwargs: Format parameters for the message
    
    Returns:
        Translated and formatted message
    """
    translations = TRANSLATIONS.get(key, {})
    message = translations.get(language, translations.get("en", key))
    
    if kwargs:
        return message.format(**kwargs)
    return message


def detect_language(accept_language: str | None) -> Language:
    """Detect language from Accept-Language header.
    
    Args:
        accept_language: Accept-Language header value
    
    Returns:
        Detected language code
    """
    if not accept_language:
        return "en"
    
    # Simple detection: check if Chinese is preferred
    if "zh" in accept_language.lower():
        return "zh"
    
    return "en"
