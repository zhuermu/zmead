"""Base class for sub-agents.

All sub-agents inherit from BaseAgent and implement the execute method.
Sub-agents are registered with the AgentRegistry and exposed as tools
to the main Gemini 3 orchestrator via function calling.

Requirements: Architecture v3.0
"""

from abc import ABC, abstractmethod
from typing import Any

import structlog
from pydantic import BaseModel

from app.services.gemini3_client import FunctionDeclaration

logger = structlog.get_logger(__name__)


class AgentContext(BaseModel):
    """Context passed to agent execution."""
    user_id: str
    session_id: str
    memory_context: dict[str, Any] | None = None


class AgentResult(BaseModel):
    """Result from agent execution."""
    success: bool
    data: dict[str, Any] = {}
    error: str | None = None
    credit_consumed: float = 0.0
    message: str = ""


class BaseAgent(ABC):
    """Base class for all sub-agents.

    Sub-agents implement specific capabilities (creative, performance, etc.)
    and are exposed as tools to the main orchestrator.

    Usage:
        class MyAgent(BaseAgent):
            name = "my_agent"
            description = "Does something useful"

            async def execute(self, action: str, params: dict, context: AgentContext) -> AgentResult:
                # Implementation
                pass
    """

    name: str = "base_agent"
    description: str = "Base agent"

    @abstractmethod
    async def execute(
        self,
        action: str,
        params: dict[str, Any],
        context: AgentContext,
    ) -> AgentResult:
        """Execute an action with given parameters.

        Args:
            action: Action name to execute
            params: Action parameters
            context: Execution context

        Returns:
            AgentResult with success/failure and data
        """
        pass

    def get_tool_declaration(self) -> FunctionDeclaration:
        """Get function declaration for Gemini function calling.

        Override this method to customize the tool schema.
        """
        return FunctionDeclaration(
            name=self.name,
            description=self.description,
            parameters=self._get_parameters_schema(),
        )

    def _get_parameters_schema(self) -> dict[str, Any]:
        """Get JSON schema for parameters.

        Override this to customize the parameters schema.
        """
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "Action to execute",
                },
                "params": {
                    "type": "object",
                    "description": "Action parameters",
                },
            },
            "required": ["action"],
        }

    async def __call__(
        self,
        action: str,
        params: dict[str, Any] | None = None,
        user_id: str = "",
        session_id: str = "",
        **kwargs,
    ) -> dict[str, Any]:
        """Callable interface for function calling.

        This allows the agent to be called directly as a function handler.
        """
        context = AgentContext(
            user_id=user_id or kwargs.get("user_id", ""),
            session_id=session_id or kwargs.get("session_id", ""),
            memory_context=kwargs.get("memory_context"),
        )

        result = await self.execute(action, params or {}, context)
        return result.model_dump()
