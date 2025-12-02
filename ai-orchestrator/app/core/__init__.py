"""Core modules for AI Orchestrator.

This package contains core infrastructure:
- config: Configuration management
- logging: Structured logging
- redis_client: Redis connection
- state: Agent state schema (legacy, for compatibility)
- context: Context management utilities
- react_agent: ReAct Agent implementation
"""

from app.core.config import Settings, get_settings
from app.core.context import (
    compress_history,
    extract_references,
    get_context_window_usage,
    resolve_reference,
)
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
from app.core.state import (
    ActionItem,
    ActionResult,
    AgentState,
    ErrorInfo,
    create_initial_state,
)

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
    # State (legacy, for compatibility)
    "AgentState",
    "ActionItem",
    "ActionResult",
    "ErrorInfo",
    "create_initial_state",
    # Context
    "extract_references",
    "resolve_reference",
    "compress_history",
    "get_context_window_usage",
    # Note: ReAct Agent should be imported directly:
    # from app.core.react_agent import ReActAgent
]
