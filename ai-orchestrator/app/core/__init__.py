"""Core modules for AI Orchestrator.

This package contains core infrastructure:
- config: Configuration management
- logging: Structured logging
- redis_client: Redis connection
- state: Agent state schema
- routing: Conditional routing logic
- context: Context management utilities
- graph: LangGraph builder
- models: Core data models (ExecutionPlan, ExecutionStep, StepResult)
"""

from app.core.config import Settings, get_settings
from app.core.context import (
    compress_history,
    extract_references,
    get_context_window_usage,
    resolve_reference,
)

# Note: graph imports are done lazily to avoid circular imports
# Use: from app.core.graph import build_agent_graph, get_agent_graph, etc.
from app.core.logging import (
    bind_context,
    clear_context,
    configure_logging,
    get_logger,
    get_request_id,
    set_request_id,
)
from app.core.models import ExecutionPlan, ExecutionStep, StepResult
from app.core.redis_client import RedisConnectionError, get_redis
from app.core.redis_client import ping as redis_ping
from app.core.routing import (
    after_respond,
    route_after_analyzer,
    route_after_executor,
    route_after_planner,
    route_after_router_v2,
)
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
    # State
    "AgentState",
    "ActionItem",
    "ActionResult",
    "ErrorInfo",
    "create_initial_state",
    # Models
    "ExecutionPlan",
    "ExecutionStep",
    "StepResult",
    # Routing
    "route_after_router_v2",
    "route_after_planner",
    "route_after_executor",
    "route_after_analyzer",
    "after_respond",
    # Context
    "extract_references",
    "resolve_reference",
    "compress_history",
    "get_context_window_usage",
    # Note: Graph functions are not exported here to avoid circular imports
    # Import directly: from app.core.graph import build_agent_graph, get_agent_graph, etc.
]
