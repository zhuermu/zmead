"""Tests for tool registry."""

import pytest

from app.tools.base import AgentTool, ToolCategory, ToolMetadata, ToolParameter
from app.tools.registry import ToolRegistry, reset_tool_registry


class MockTool(AgentTool):
    """Mock tool for testing."""

    def __init__(self, name: str, category: ToolCategory, tags: list[str] | None = None):
        metadata = ToolMetadata(
            name=name,
            description=f"Mock tool: {name}",
            category=category,
            parameters=[],
            tags=tags or [],
        )
        super().__init__(metadata)

    async def execute(self, parameters: dict, context: dict | None = None):
        return {"success": True, "tool": self.name}


def test_registry_register_tool():
    """Test registering a tool."""
    reset_tool_registry()
    registry = ToolRegistry()

    tool = MockTool("test_tool", ToolCategory.AGENT_CUSTOM, tags=["test"])
    registry.register(tool)

    assert registry.has_tool("test_tool")
    assert registry.get_tool("test_tool") == tool


def test_registry_duplicate_registration():
    """Test that duplicate registration raises error."""
    reset_tool_registry()
    registry = ToolRegistry()

    tool1 = MockTool("test_tool", ToolCategory.AGENT_CUSTOM)
    tool2 = MockTool("test_tool", ToolCategory.LANGCHAIN)

    registry.register(tool1)

    with pytest.raises(ValueError, match="already registered"):
        registry.register(tool2)


def test_registry_get_tools_by_category():
    """Test getting tools by category."""
    reset_tool_registry()
    registry = ToolRegistry()

    tool1 = MockTool("tool1", ToolCategory.AGENT_CUSTOM)
    tool2 = MockTool("tool2", ToolCategory.LANGCHAIN)
    tool3 = MockTool("tool3", ToolCategory.AGENT_CUSTOM)

    registry.register(tool1)
    registry.register(tool2)
    registry.register(tool3)

    custom_tools = registry.get_tools_by_category(ToolCategory.AGENT_CUSTOM)
    assert len(custom_tools) == 2
    assert tool1 in custom_tools
    assert tool3 in custom_tools

    langchain_tools = registry.get_tools_by_category(ToolCategory.LANGCHAIN)
    assert len(langchain_tools) == 1
    assert tool2 in langchain_tools


def test_registry_get_tools_by_tags():
    """Test getting tools by tags."""
    reset_tool_registry()
    registry = ToolRegistry()

    tool1 = MockTool("tool1", ToolCategory.AGENT_CUSTOM, tags=["creative", "image"])
    tool2 = MockTool("tool2", ToolCategory.AGENT_CUSTOM, tags=["creative", "video"])
    tool3 = MockTool("tool3", ToolCategory.AGENT_CUSTOM, tags=["performance"])

    registry.register(tool1)
    registry.register(tool2)
    registry.register(tool3)

    # Match any tag
    creative_tools = registry.get_tools_by_tags(["creative"], match_all=False)
    assert len(creative_tools) == 2
    assert tool1 in creative_tools
    assert tool2 in creative_tools

    # Match all tags
    image_creative_tools = registry.get_tools_by_tags(["creative", "image"], match_all=True)
    assert len(image_creative_tools) == 1
    assert tool1 in image_creative_tools


def test_registry_unregister():
    """Test unregistering a tool."""
    reset_tool_registry()
    registry = ToolRegistry()

    tool = MockTool("test_tool", ToolCategory.AGENT_CUSTOM, tags=["test"])
    registry.register(tool)

    assert registry.has_tool("test_tool")

    registry.unregister("test_tool")

    assert not registry.has_tool("test_tool")
    assert registry.get_tool("test_tool") is None


def test_registry_stats():
    """Test registry statistics."""
    reset_tool_registry()
    registry = ToolRegistry()

    tool1 = MockTool("tool1", ToolCategory.AGENT_CUSTOM, tags=["creative"])
    tool2 = MockTool("tool2", ToolCategory.LANGCHAIN, tags=["search"])
    tool3 = MockTool("tool3", ToolCategory.MCP_SERVER, tags=["data"])

    registry.register(tool1)
    registry.register(tool2)
    registry.register(tool3)

    stats = registry.get_stats()

    assert stats["total_tools"] == 3
    assert stats["by_category"]["agent_custom"] == 1
    assert stats["by_category"]["langchain"] == 1
    assert stats["by_category"]["mcp_server"] == 1
    assert "creative" in stats["tags"]
    assert "search" in stats["tags"]
    assert "data" in stats["tags"]
