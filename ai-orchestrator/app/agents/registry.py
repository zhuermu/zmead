"""Agent registry for managing sub-agents.

The registry maintains all available sub-agents and provides:
- Registration and lookup
- Tool declarations for Gemini function calling
- Handler mapping for execution

Requirements: Architecture v3.0
"""

from typing import Any, Callable

import structlog

from app.agents.base import BaseAgent
from app.services.gemini3_client import FunctionDeclaration

logger = structlog.get_logger(__name__)


class AgentRegistry:
    """Central registry for all sub-agents.

    Usage:
        registry = get_agent_registry()

        # Register agents
        registry.register(CreativeAgent())
        registry.register(PerformanceAgent())

        # Get tool declarations for Gemini
        tools = registry.get_tool_declarations()

        # Get handlers for function calling
        handlers = registry.get_tool_handlers()
    """

    _instance: "AgentRegistry | None" = None
    _agents: dict[str, BaseAgent]

    def __new__(cls) -> "AgentRegistry":
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._agents = {}
        return cls._instance

    def register(self, agent: BaseAgent) -> None:
        """Register a sub-agent.

        Args:
            agent: Agent instance to register
        """
        name = agent.name

        if name in self._agents:
            logger.warning("agent_registry_overwrite", name=name)

        self._agents[name] = agent
        logger.info("agent_registry_registered", name=name)

    def unregister(self, name: str) -> bool:
        """Unregister an agent.

        Args:
            name: Agent name to unregister

        Returns:
            True if agent was removed
        """
        if name in self._agents:
            del self._agents[name]
            logger.info("agent_registry_unregistered", name=name)
            return True
        return False

    def get(self, name: str) -> BaseAgent | None:
        """Get an agent by name."""
        return self._agents.get(name)

    def list_agents(self) -> list[BaseAgent]:
        """List all registered agents."""
        return list(self._agents.values())

    def get_tool_declarations(self) -> list[FunctionDeclaration]:
        """Get function declarations for all agents.

        Returns:
            List of FunctionDeclaration for Gemini function calling
        """
        return [agent.get_tool_declaration() for agent in self._agents.values()]

    def get_tool_handlers(self, user_id: str, session_id: str) -> dict[str, Callable]:
        """Get handler functions for all agents.

        Creates callable handlers that include user context.

        Args:
            user_id: User ID for context
            session_id: Session ID for context

        Returns:
            Dict mapping agent names to async handler functions
        """
        handlers = {}

        for name, agent in self._agents.items():
            # Create a closure that captures user context
            async def handler(
                action: str,
                params: dict[str, Any] | None = None,
                _agent: BaseAgent = agent,
                _user_id: str = user_id,
                _session_id: str = session_id,
                **kwargs,
            ) -> dict[str, Any]:
                return await _agent(
                    action=action,
                    params=params,
                    user_id=_user_id,
                    session_id=_session_id,
                    **kwargs,
                )

            handlers[name] = handler

        return handlers

    def clear(self) -> None:
        """Clear all registered agents (for testing)."""
        self._agents.clear()
        logger.info("agent_registry_cleared")

    def __len__(self) -> int:
        return len(self._agents)

    def __contains__(self, name: str) -> bool:
        return name in self._agents


# Global registry instance
_registry: AgentRegistry | None = None


def get_agent_registry() -> AgentRegistry:
    """Get the global agent registry instance."""
    global _registry
    if _registry is None:
        _registry = AgentRegistry()
    return _registry


def reset_agent_registry() -> None:
    """Reset the global registry (for testing)."""
    global _registry
    if _registry is not None:
        _registry.clear()
    _registry = None
