"""Base classes for the unified tool layer.

This module defines the core abstractions for tools:
- ToolDefinition: Metadata about a tool (name, description, parameters, etc.)
- ToolContext: Runtime context passed to tool execution
- ToolResult: Standardized result from tool execution
- BaseTool: Abstract base class for all tools

All tools must inherit from BaseTool and implement the execute() method.

Requirements: Architecture v2.0 - Unified Tool Layer
"""

from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field


class ToolCategory(str, Enum):
    """Tool category for organization and filtering."""

    DATA = "data"  # Data retrieval tools (get_ad_performance, etc.)
    ANALYSIS = "analysis"  # Analysis tools (analyze_anomaly, etc.)
    CREATIVE = "creative"  # Creative generation tools
    ACTION = "action"  # Action tools (create_campaign, pause, etc.)
    MARKET = "market"  # Market intelligence tools
    WEB = "web"  # Web scraping tools
    UTILITY = "utility"  # Utility tools


class ToolRiskLevel(str, Enum):
    """Risk level for tool operations."""

    LOW = "low"  # Read-only operations, no side effects
    MEDIUM = "medium"  # Reversible operations (create, update)
    HIGH = "high"  # Irreversible or high-impact operations (delete, pause_all)


class ToolDefinition(BaseModel):
    """Metadata definition for a tool.

    This is used for:
    - LLM tool calling (generating function descriptions)
    - Tool discovery and filtering
    - Credit estimation
    - Confirmation requirements

    Attributes:
        name: Unique tool identifier
        description: Human-readable description for LLM understanding
        category: Tool category for organization
        risk_level: Risk level for confirmation requirements
        credit_cost: Base credit cost per execution
        requires_confirmation: Whether user confirmation is needed
        parameters: JSON Schema for input parameters
        returns: JSON Schema for return value
    """

    name: str = Field(description="Unique tool identifier")
    description: str = Field(description="Tool description for LLM")
    category: ToolCategory
    risk_level: ToolRiskLevel = ToolRiskLevel.LOW
    credit_cost: float = Field(default=0.0, description="Base credit cost")
    requires_confirmation: bool = Field(default=False)
    parameters: dict[str, Any] = Field(
        default_factory=dict, description="Input JSON Schema"
    )
    returns: dict[str, Any] = Field(
        default_factory=dict, description="Output JSON Schema"
    )

    def to_openai_function(self) -> dict[str, Any]:
        """Convert to OpenAI function calling format.

        Returns:
            Dict compatible with OpenAI's function calling schema
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class ToolContext(BaseModel):
    """Runtime context for tool execution.

    Passed to every tool execution with user/session info
    and results from previous steps.

    Attributes:
        user_id: Current user identifier
        session_id: Current session identifier
        previous_results: Results from previous steps (step_id -> result)
        memory_context: Retrieved memory context for personalization
        metadata: Additional metadata
    """

    user_id: str
    session_id: str
    previous_results: dict[int, Any] = Field(default_factory=dict)
    memory_context: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ToolResult(BaseModel):
    """Standardized result from tool execution.

    All tools return this structure for consistent handling.

    Attributes:
        success: Whether execution succeeded
        data: Result data (tool-specific)
        error: Error message if failed
        credit_consumed: Actual credits consumed
        execution_time: Execution duration in seconds
        metadata: Additional result metadata
    """

    success: bool
    data: Any = None
    error: str | None = None
    credit_consumed: float = 0.0
    execution_time: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def success_result(
        cls,
        data: Any,
        credit_consumed: float = 0.0,
        execution_time: float = 0.0,
        **metadata: Any,
    ) -> "ToolResult":
        """Create a successful result."""
        return cls(
            success=True,
            data=data,
            credit_consumed=credit_consumed,
            execution_time=execution_time,
            metadata=metadata,
        )

    @classmethod
    def error_result(
        cls,
        error: str,
        data: Any = None,
        **metadata: Any,
    ) -> "ToolResult":
        """Create an error result."""
        return cls(
            success=False,
            data=data,
            error=error,
            metadata=metadata,
        )


# Type variables for generic tool input/output
InputT = TypeVar("InputT", bound=BaseModel)
OutputT = TypeVar("OutputT", bound=BaseModel)


class BaseTool(ABC, Generic[InputT, OutputT]):
    """Abstract base class for all tools.

    All tools must inherit from this class and implement:
    - definition: Class attribute with ToolDefinition
    - execute(): Async method that performs the tool's action

    Optional overrides:
    - estimate_cost(): Calculate credit cost based on parameters
    - validate_params(): Custom parameter validation

    Example:
        class GenerateCreativeTool(BaseTool[GenerateCreativeInput, GenerateCreativeOutput]):
            definition = ToolDefinition(
                name="generate_creative",
                description="Generate ad creative images",
                category=ToolCategory.CREATIVE,
                credit_cost=0.5,
                parameters=GenerateCreativeInput.model_json_schema(),
                returns=GenerateCreativeOutput.model_json_schema(),
            )

            async def execute(self, params: GenerateCreativeInput, context: ToolContext) -> ToolResult:
                # Implementation
                ...
    """

    # Subclasses must define this
    definition: ToolDefinition

    @abstractmethod
    async def execute(self, params: InputT, context: ToolContext) -> ToolResult:
        """Execute the tool with given parameters.

        Args:
            params: Validated input parameters
            context: Runtime context (user, session, previous results)

        Returns:
            ToolResult with success/error status and data
        """
        pass

    def estimate_cost(self, params: InputT) -> float:
        """Estimate credit cost for given parameters.

        Override this for tools with variable cost (e.g., per-image pricing).

        Args:
            params: Input parameters

        Returns:
            Estimated credit cost
        """
        return self.definition.credit_cost

    def validate_params(self, params: dict[str, Any]) -> InputT:
        """Validate and parse input parameters.

        Override for custom validation logic.

        Args:
            params: Raw parameter dict

        Returns:
            Validated params as InputT model

        Raises:
            ValidationError: If validation fails
        """
        # Get the input type from Generic annotation
        # This is a simplified version - in practice you'd use get_args()
        raise NotImplementedError(
            "Subclasses should implement validate_params or use Pydantic directly"
        )

    def requires_confirmation_for(self, params: InputT) -> bool:
        """Check if this specific call requires confirmation.

        Override for dynamic confirmation (e.g., large budget changes).

        Args:
            params: Input parameters

        Returns:
            True if confirmation is required
        """
        return self.definition.requires_confirmation

    def get_name(self) -> str:
        """Get tool name."""
        return self.definition.name

    def get_description(self) -> str:
        """Get tool description."""
        return self.definition.description

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name={self.definition.name})>"
