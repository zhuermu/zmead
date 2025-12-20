"""Core modules for AI Orchestrator.

This package contains core infrastructure:
- config: Configuration management
- logging: Structured logging
- redis_client: Redis connection
- strands_agent: Strands Agent implementation (ReAct pattern)
- messages: Simple message types for AI interactions

Legacy modules (not imported by default):
- state: Agent state schema (legacy, requires langchain)
- context: Context management utilities (legacy, requires langchain)
- react_agent: ReAct Agent implementation (legacy, requires langchain)
"""

from app.core.config import Settings, get_settings
from app.core.logging import (
    bind_context,
    clear_context,
    configure_logging,
    get_logger,
    get_request_id,
    set_request_id,
)
from app.core.redis_client import RedisConnectionError, get_redis
from app.core.redis_client import ping as redis_ping

# Import message types
from app.core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

# Note: Legacy modules with langchain dependencies are not imported by default.
# Import them explicitly if needed:
# from app.core.context import compress_history, extract_references, ...
# from app.core.state import AgentState, ActionItem, ...
# from app.core.react_agent import ReActAgent

__all__ = [
    # Config
    "Settings",
    "get_settings",
    # Logging
    "configure_logging",
    "get_logger",
    "get_request_id",
    "set_request_id",
    "bind_context",
    "clear_context",
    # Redis
    "RedisConnectionError",
    "get_redis",
    "redis_ping",
    # Messages
    "BaseMessage",
    "HumanMessage",
    "AIMessage",
    "SystemMessage",
    # Note: Strands Agent should be imported directly:
    # from app.core.strands_agent import StrandsReActAgent
    # Legacy modules with langchain dependencies:
    # from app.core.react_agent import ReActAgent
    # from app.core.state import AgentState, ActionItem, ...
    # from app.core.context import extract_references, ...
]
