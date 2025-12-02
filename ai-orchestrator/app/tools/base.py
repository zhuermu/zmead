"""Base classes and interfaces for the 3-category Tools architecture.

This module defines the unified interface for all three types of tools:
1. LangChain Tools - Built-in tools from LangChain framework
2. Agent Custom Tools - Custom tools that can call LLMs
3. MCP Server Tools - Backend API tools via MCP protocol
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Callable

from pydantic import BaseModel, Field


class ToolCategory(str, Enum):
    """Tool category enumeration."""

    LANGCHAIN = "langchain"  # LangChain built-in tools
    AGENT_CUSTOM = "agent_custom"  # Agent custom tools (can call LLMs)
    MCP_SERVER = "mcp_server"  # MCP Server tools (backend API)


class ToolParameter(BaseModel):
    """Tool parameter definition.

    Defines a single parameter for a tool, including its type,
    description, and whether it's required.
    """

    name: str = Field(..., description="Parameter name")
    type: str = Field(..., description="Parameter type (string, number, boolean, object, array)")
    description: str = Field(..., description="Parameter description")
    required: bool = Field(default=True, description="Whether parameter is required")
    default: Any | None = Field(default=None, description="Default value if not required")
    enum: list[str] | None = Field(default=None, description="Allowed values (for enum types)")


class ToolMetadata(BaseModel):
    """Tool metadata definition.

    Contains all metadata about a tool including its name, description,
    parameters, and category.
    """

    name: str = Field(..., description="Tool name (unique identifier)")
    description: str = Field(..., description="Tool description for LLM")
    category: ToolCategory = Field(..., description="Tool category")
    parameters: list[ToolParameter] = Field(
        default_factory=list,
        description="Tool parameters",
    )
    returns: str = Field(default="object", description="Return type description")
    examples: list[dict[str, Any]] | None = Field(
        default=None,
        description="Example usage for LLM",
    )

    # Additional metadata
    credit_cost: float | None = Field(
        default=None,
        description="Credit cost for this tool (if applicable)",
    )
    requires_confirmation: bool = Field(
        default=False,
        description="Whether this tool requires user confirmation",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Tags for categorization and search",
    )


class AgentTool(ABC):
    """Base class for all agent tools.

    This abstract base class defines the interface that all tools must implement,
    regardless of their category (LangChain, Agent Custom, or MCP Server).

    Attributes:
        metadata: Tool metadata including name, description, parameters
    """

    def __init__(self, metadata: ToolMetadata):
        """Initialize tool with metadata.

        Args:
            metadata: Tool metadata
        """
        self.metadata = metadata

    @property
    def name(self) -> str:
        """Get tool name."""
        return self.metadata.name

    @property
    def description(self) -> str:
        """Get tool description."""
        return self.metadata.description

    @property
    def category(self) -> ToolCategory:
        """Get tool category."""
        return self.metadata.category

    @abstractmethod
    async def execute(
        self,
        parameters: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> Any:
        """Execute the tool with given parameters.

        Args:
            parameters: Tool parameters
            context: Optional execution context (user_id, session_id, etc.)

        Returns:
            Tool execution result

        Raises:
            ToolExecutionError: If execution fails
        """
        pass

    def to_langchain_tool(self) -> Callable:
        """Convert to LangChain tool format.

        Returns a callable that can be used by LangChain agents.

        Returns:
            Callable function for LangChain
        """
        async def tool_func(**kwargs) -> Any:
            return await self.execute(kwargs)

        # Set function metadata for LangChain
        tool_func.__name__ = self.name
        tool_func.__doc__ = self.description

        return tool_func

    def to_dict(self) -> dict[str, Any]:
        """Convert tool to dictionary representation.

        Returns:
            Dictionary with tool metadata
        """
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "parameters": [param.model_dump() for param in self.metadata.parameters],
            "returns": self.metadata.returns,
            "credit_cost": self.metadata.credit_cost,
            "requires_confirmation": self.metadata.requires_confirmation,
            "tags": self.metadata.tags,
        }


class ToolExecutionError(Exception):
    """Exception raised when tool execution fails."""

    def __init__(
        self,
        message: str,
        tool_name: str,
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        """Initialize tool execution error.

        Args:
            message: Error message
            tool_name: Name of the tool that failed
            error_code: Optional error code
            details: Optional error details
        """
        super().__init__(message)
        self.message = message
        self.tool_name = tool_name
        self.error_code = error_code
        self.details = details or {}
