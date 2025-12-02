"""Agent setup and registration.

This module initializes and registers all sub-agents with the registry.

Requirements: Architecture v3.0
"""

import structlog

from app.agents.registry import get_agent_registry
from app.agents.creative import get_creative_agent
from app.agents.performance import get_performance_agent
from app.agents.market import get_market_agent
from app.agents.landing_page import get_landing_page_agent
from app.agents.campaign import get_campaign_agent

logger = structlog.get_logger(__name__)

_agents_registered = False


def register_all_agents() -> None:
    """Register all sub-agents with the registry.

    This should be called once at application startup.
    """
    global _agents_registered

    if _agents_registered:
        return

    registry = get_agent_registry()

    # Register all agents
    agents = [
        get_creative_agent(),
        get_performance_agent(),
        get_market_agent(),
        get_landing_page_agent(),
        get_campaign_agent(),
    ]

    for agent in agents:
        registry.register(agent)

    _agents_registered = True

    logger.info(
        "agents_registered",
        count=len(registry),
        agents=registry.list_agents(),
    )


def reset_agents() -> None:
    """Reset all agents (for testing)."""
    global _agents_registered
    _agents_registered = False

    from app.agents.registry import reset_agent_registry
    reset_agent_registry()
