"""MCP Tool Registry for managing and discovering tools."""

from collections.abc import Awaitable, Callable
from typing import Any

from app.mcp.types import MCPToolDefinition, MCPToolParameter

# Type alias for tool handler functions
ToolHandler = Callable[..., Awaitable[Any]]


class ToolRegistry:
    """Registry for MCP tools.
    
    Manages tool registration, discovery, and metadata.
    """

    _instance: "ToolRegistry | None" = None

    def __new__(cls) -> "ToolRegistry":
        """Singleton pattern for global tool registry."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._tools: dict[str, MCPToolDefinition] = {}
            cls._instance._handlers: dict[str, ToolHandler] = {}
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset the registry (mainly for testing)."""
        if cls._instance:
            cls._instance._tools = {}
            cls._instance._handlers = {}

    def register(
        self,
        name: str,
        description: str,
        handler: ToolHandler,
        parameters: list[MCPToolParameter] | None = None,
        category: str = "general",
        requires_auth: bool = True,
    ) -> None:
        """Register a new tool.
        
        Args:
            name: Unique tool name
            description: Tool description
            handler: Async function to handle tool execution
            parameters: List of parameter definitions
            category: Tool category for grouping
            requires_auth: Whether tool requires authentication
        """
        tool_def = MCPToolDefinition(
            name=name,
            description=description,
            parameters=parameters or [],
            category=category,
            requires_auth=requires_auth,
        )

        self._tools[name] = tool_def
        self._handlers[name] = handler

    def unregister(self, name: str) -> bool:
        """Unregister a tool.
        
        Args:
            name: Tool name to unregister
            
        Returns:
            True if tool was unregistered, False if not found
        """
        if name in self._tools:
            del self._tools[name]
            del self._handlers[name]
            return True
        return False

    def get_tool(self, name: str) -> MCPToolDefinition | None:
        """Get tool definition by name.
        
        Args:
            name: Tool name
            
        Returns:
            Tool definition or None if not found
        """
        return self._tools.get(name)

    def get_handler(self, name: str) -> ToolHandler | None:
        """Get tool handler by name.
        
        Args:
            name: Tool name
            
        Returns:
            Tool handler function or None if not found
        """
        return self._handlers.get(name)

    def list_tools(
        self,
        category: str | None = None,
    ) -> list[MCPToolDefinition]:
        """List all registered tools.
        
        Args:
            category: Optional category filter
            
        Returns:
            List of tool definitions
        """
        tools = list(self._tools.values())

        if category:
            tools = [t for t in tools if t.category == category]

        return sorted(tools, key=lambda t: (t.category, t.name))

    def get_categories(self) -> list[str]:
        """Get all unique tool categories.
        
        Returns:
            Sorted list of category names
        """
        categories = set(t.category for t in self._tools.values())
        return sorted(categories)

    def has_tool(self, name: str) -> bool:
        """Check if a tool is registered.
        
        Args:
            name: Tool name
            
        Returns:
            True if tool exists
        """
        return name in self._tools


def tool(
    name: str,
    description: str,
    parameters: list[MCPToolParameter] | None = None,
    category: str = "general",
    requires_auth: bool = True,
) -> Callable[[ToolHandler], ToolHandler]:
    """Decorator for registering MCP tools.
    
    Usage:
        @tool(
            name="get_creatives",
            description="Get list of creatives",
            parameters=[
                MCPToolParameter(name="page", type="integer", required=False),
            ],
            category="creative",
        )
        async def get_creatives(user_id: int, db: AsyncSession, page: int = 1):
            ...
    """
    def decorator(func: ToolHandler) -> ToolHandler:
        registry = ToolRegistry()
        registry.register(
            name=name,
            description=description,
            handler=func,
            parameters=parameters,
            category=category,
            requires_auth=requires_auth,
        )
        return func

    return decorator


# Global registry instance
registry = ToolRegistry()
