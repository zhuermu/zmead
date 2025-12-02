"""Tool Registry - Central registry for all available tools.

This module provides the ToolRegistry class that manages tool registration,
discovery, and lookup. It serves as the single source of truth for available
tools in the system.

Features:
- Register/unregister tools
- Lookup by name or category
- Generate LLM-compatible tool descriptions
- Integration with MCP Hub for external tools

Requirements: Architecture v2.0 - Unified Tool Layer
"""

import structlog
from typing import Any

from app.tools.base import BaseTool, ToolCategory, ToolDefinition

logger = structlog.get_logger(__name__)


class ToolRegistry:
    """Central registry for all tools.

    Manages tool registration and provides lookup functionality.
    Singleton pattern ensures consistent tool availability across the system.

    Usage:
        registry = get_tool_registry()

        # Register a tool
        registry.register(GenerateCreativeTool())

        # Get a tool
        tool = registry.get("generate_creative")

        # List all tools
        tools = registry.list_tools()

        # Get tools for LLM
        functions = registry.get_tools_for_llm()
    """

    _instance: "ToolRegistry | None" = None
    _tools: dict[str, BaseTool]

    def __new__(cls) -> "ToolRegistry":
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._tools = {}
        return cls._instance

    def register(self, tool: BaseTool) -> None:
        """Register a tool.

        Args:
            tool: Tool instance to register

        Raises:
            ValueError: If tool with same name already registered
        """
        name = tool.definition.name

        if name in self._tools:
            logger.warning("tool_registry_overwrite", name=name)

        self._tools[name] = tool
        logger.info(
            "tool_registry_registered",
            name=name,
            category=tool.definition.category.value,
        )

    def unregister(self, name: str) -> bool:
        """Unregister a tool.

        Args:
            name: Tool name to unregister

        Returns:
            True if tool was removed, False if not found
        """
        if name in self._tools:
            del self._tools[name]
            logger.info("tool_registry_unregistered", name=name)
            return True
        return False

    def get(self, name: str) -> BaseTool | None:
        """Get a tool by name.

        Args:
            name: Tool name

        Returns:
            Tool instance or None if not found
        """
        return self._tools.get(name)

    def get_required(self, name: str) -> BaseTool:
        """Get a tool by name, raising if not found.

        Args:
            name: Tool name

        Returns:
            Tool instance

        Raises:
            ValueError: If tool not found
        """
        tool = self.get(name)
        if tool is None:
            raise ValueError(f"Tool not found: {name}")
        return tool

    def list_tools(self) -> list[BaseTool]:
        """List all registered tools.

        Returns:
            List of all tool instances
        """
        return list(self._tools.values())

    def list_definitions(self) -> list[ToolDefinition]:
        """List all tool definitions.

        Returns:
            List of all tool definitions
        """
        return [tool.definition for tool in self._tools.values()]

    def list_by_category(self, category: ToolCategory) -> list[BaseTool]:
        """List tools by category.

        Args:
            category: Category to filter by

        Returns:
            List of tools in the category
        """
        return [
            tool
            for tool in self._tools.values()
            if tool.definition.category == category
        ]

    def list_names(self) -> list[str]:
        """List all tool names.

        Returns:
            List of tool names
        """
        return list(self._tools.keys())

    def get_tools_for_llm(self) -> list[dict[str, Any]]:
        """Get tool descriptions in OpenAI function calling format.

        Returns:
            List of function definitions for LLM tool calling
        """
        return [tool.definition.to_openai_function() for tool in self._tools.values()]

    def get_tools_for_llm_by_category(
        self, categories: list[ToolCategory]
    ) -> list[dict[str, Any]]:
        """Get tool descriptions filtered by categories.

        Args:
            categories: Categories to include

        Returns:
            List of function definitions
        """
        return [
            tool.definition.to_openai_function()
            for tool in self._tools.values()
            if tool.definition.category in categories
        ]

    def clear(self) -> None:
        """Clear all registered tools (mainly for testing)."""
        self._tools.clear()
        logger.info("tool_registry_cleared")

    def __len__(self) -> int:
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        return name in self._tools


# Global registry instance
_registry: ToolRegistry | None = None


def get_tool_registry() -> ToolRegistry:
    """Get the global tool registry instance.

    Returns:
        ToolRegistry singleton instance
    """
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry


def reset_tool_registry() -> None:
    """Reset the global registry (for testing)."""
    global _registry
    if _registry is not None:
        _registry.clear()
    _registry = None
