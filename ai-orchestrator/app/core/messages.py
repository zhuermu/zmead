"""Simple message types to replace langchain_core.messages.

This module provides lightweight message classes for AI interactions,
replacing the dependency on langchain_core.
"""

from typing import Any


class BaseMessage:
    """Base class for all messages."""

    def __init__(self, content: str, **kwargs: Any):
        """Initialize base message.

        Args:
            content: Message content
            **kwargs: Additional message attributes
        """
        self.content = content
        self.additional_kwargs = kwargs

    def __str__(self) -> str:
        """String representation."""
        return self.content

    def __repr__(self) -> str:
        """Debug representation."""
        return f"{self.__class__.__name__}(content={self.content!r})"


class HumanMessage(BaseMessage):
    """Message from a human user."""

    type: str = "human"


class AIMessage(BaseMessage):
    """Message from the AI assistant."""

    type: str = "ai"


class SystemMessage(BaseMessage):
    """System message (instructions, context)."""

    type: str = "system"


__all__ = [
    "BaseMessage",
    "HumanMessage",
    "AIMessage",
    "SystemMessage",
]
