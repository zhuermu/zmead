"""Tool registry for managing and discovering tools.

This module provides the ToolRegistry class for registering, discovering,
and managing all three categories of tools:
1. LangChain built-in tools
2. Agent custom tools
3. MCP Server tools
"""

import structlog
from typing import Any

from app.tools.base import AgentTool, ToolCategory, ToolMetadata

logger = structlog.get_logger(__name__)


class ToolRegistry:
    """Registry for managing all agent tools.

    The registry maintains a catalog of all available tools across
    the three categories and provides methods for registration,
    lookup, and filtering.

    Example:
        registry = ToolRegistry()

        # Register a custom tool
        registry.register(my_custom_tool)

        # Get tool by name
        tool = registry.get_tool("generate_image_tool")

        # Get all tools in a category
        custom_tools = registry.get_tools_by_category(ToolCategory.AGENT_CUSTOM)

        # Get tools by tags
        creative_tools = registry.get_tools_by_tags(["creative", "image"])
    """

    def __init__(self):
        """Initialize the tool registry."""
        # Tool storage: name -> AgentTool
        self._tools: dict[str, AgentTool] = {}

        # Category index: category -> set of tool names
        self._category_index: dict[ToolCategory, set[str]] = {
            ToolCategory.LANGCHAIN: set(),
            ToolCategory.AGENT_CUSTOM: set(),
            ToolCategory.MCP_SERVER: set(),
        }

        # Tag index: tag -> set of tool names
        self._tag_index: dict[str, set[str]] = {}

        logger.info("tool_registry_initialized")

    def register(self, tool: AgentTool) -> None:
        """Register a tool in the registry.

        Args:
            tool: Tool to register

        Raises:
            ValueError: If tool with same name already exists
        """
        if tool.name in self._tools:
            logger.warning(
                "tool_already_registered",
                tool_name=tool.name,
                category=tool.category.value,
            )
            raise ValueError(f"Tool '{tool.name}' is already registered")

        # Store tool
        self._tools[tool.name] = tool

        # Update category index
        self._category_index[tool.category].add(tool.name)

        # Update tag index
        for tag in tool.metadata.tags:
            if tag not in self._tag_index:
                self._tag_index[tag] = set()
            self._tag_index[tag].add(tool.name)

        logger.info(
            "tool_registered",
            tool_name=tool.name,
            category=tool.category.value,
            tags=tool.metadata.tags,
        )

    def register_batch(self, tools: list[AgentTool]) -> None:
        """Register multiple tools at once.

        Args:
            tools: List of tools to register
        """
        for tool in tools:
            try:
                self.register(tool)
            except ValueError as e:
                logger.error(
                    "tool_registration_failed",
                    tool_name=tool.name,
                    error=str(e),
                )

    def unregister(self, tool_name: str) -> None:
        """Unregister a tool from the registry.

        Args:
            tool_name: Name of tool to unregister
        """
        if tool_name not in self._tools:
            logger.warning("tool_not_found", tool_name=tool_name)
            return

        tool = self._tools[tool_name]

        # Remove from category index
        self._category_index[tool.category].discard(tool_name)

        # Remove from tag index
        for tag in tool.metadata.tags:
            if tag in self._tag_index:
                self._tag_index[tag].discard(tool_name)
                if not self._tag_index[tag]:
                    del self._tag_index[tag]

        # Remove tool
        del self._tools[tool_name]

        logger.info("tool_unregistered", tool_name=tool_name)

    def get_tool(self, tool_name: str) -> AgentTool | None:
        """Get a tool by name.

        Args:
            tool_name: Name of the tool

        Returns:
            Tool instance or None if not found
        """
        return self._tools.get(tool_name)

    def has_tool(self, tool_name: str) -> bool:
        """Check if a tool is registered.

        Args:
            tool_name: Name of the tool

        Returns:
            True if tool is registered
        """
        return tool_name in self._tools

    def get_all_tools(self) -> list[AgentTool]:
        """Get all registered tools.

        Returns:
            List of all tools
        """
        return list(self._tools.values())

    def get_tools_by_category(self, category: ToolCategory) -> list[AgentTool]:
        """Get all tools in a specific category.

        Args:
            category: Tool category

        Returns:
            List of tools in the category
        """
        tool_names = self._category_index.get(category, set())
        return [self._tools[name] for name in tool_names if name in self._tools]

    def get_tools_by_tags(
        self,
        tags: list[str],
        match_all: bool = False,
    ) -> list[AgentTool]:
        """Get tools that match given tags.

        Args:
            tags: List of tags to match
            match_all: If True, tool must have all tags. If False, any tag matches.

        Returns:
            List of matching tools
        """
        if not tags:
            return []

        if match_all:
            # Tool must have all tags
            matching_names = None
            for tag in tags:
                tag_tools = self._tag_index.get(tag, set())
                if matching_names is None:
                    matching_names = tag_tools.copy()
                else:
                    matching_names &= tag_tools

            if matching_names is None:
                return []

            return [self._tools[name] for name in matching_names if name in self._tools]
        else:
            # Tool must have at least one tag
            matching_names = set()
            for tag in tags:
                matching_names |= self._tag_index.get(tag, set())

            return [self._tools[name] for name in matching_names if name in self._tools]

    def get_tools_by_names(self, tool_names: list[str]) -> list[AgentTool]:
        """Get multiple tools by their names.

        Args:
            tool_names: List of tool names

        Returns:
            List of found tools (skips missing tools)
        """
        tools = []
        for name in tool_names:
            tool = self.get_tool(name)
            if tool:
                tools.append(tool)
            else:
                logger.warning("tool_not_found_in_batch", tool_name=name)

        return tools

    def list_tool_names(
        self,
        category: ToolCategory | None = None,
    ) -> list[str]:
        """List all tool names, optionally filtered by category.

        Args:
            category: Optional category filter

        Returns:
            List of tool names
        """
        if category is None:
            return list(self._tools.keys())

        return list(self._category_index.get(category, set()))

    def get_tool_metadata(self, tool_name: str) -> ToolMetadata | None:
        """Get metadata for a tool.

        Args:
            tool_name: Name of the tool

        Returns:
            Tool metadata or None if not found
        """
        tool = self.get_tool(tool_name)
        return tool.metadata if tool else None

    def get_all_metadata(self) -> list[dict[str, Any]]:
        """Get metadata for all registered tools.

        Returns:
            List of tool metadata dictionaries
        """
        return [tool.to_dict() for tool in self._tools.values()]

    def get_metadata_by_category(
        self,
        category: ToolCategory,
    ) -> list[dict[str, Any]]:
        """Get metadata for all tools in a category.

        Args:
            category: Tool category

        Returns:
            List of tool metadata dictionaries
        """
        tools = self.get_tools_by_category(category)
        return [tool.to_dict() for tool in tools]

    def clear(self) -> None:
        """Clear all registered tools."""
        self._tools.clear()
        for category in self._category_index:
            self._category_index[category].clear()
        self._tag_index.clear()

        logger.info("tool_registry_cleared")

    def get_stats(self) -> dict[str, Any]:
        """Get registry statistics.

        Returns:
            Dictionary with registry stats
        """
        return {
            "total_tools": len(self._tools),
            "by_category": {
                category.value: len(tools)
                for category, tools in self._category_index.items()
            },
            "total_tags": len(self._tag_index),
            "tags": list(self._tag_index.keys()),
        }


# Global registry instance
_global_registry: ToolRegistry | None = None


def get_tool_registry() -> ToolRegistry:
    """Get the global tool registry instance.

    Returns:
        Global ToolRegistry instance
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = ToolRegistry()
    return _global_registry


def reset_tool_registry() -> None:
    """Reset the global tool registry (mainly for testing)."""
    global _global_registry
    _global_registry = None
