"""Unified Tool Layer for AI Orchestrator.

This package provides a standardized tool abstraction that enables:
- Consistent tool definition with metadata
- Unified execution with credit management
- Easy extension through Tool Registry
- Integration with MCP Hub for external tools

Usage:
    from app.tools import get_tool_registry, BaseTool

    # Get a tool
    registry = get_tool_registry()
    tool = registry.get("generate_creative")

    # Execute
    result = await tool.execute(params, context)
"""

from app.tools.base import (
    BaseTool,
    ToolCategory,
    ToolContext,
    ToolDefinition,
    ToolResult,
    ToolRiskLevel,
)
from app.tools.registry import ToolRegistry, get_tool_registry

__all__ = [
    "BaseTool",
    "ToolCategory",
    "ToolContext",
    "ToolDefinition",
    "ToolResult",
    "ToolRiskLevel",
    "ToolRegistry",
    "get_tool_registry",
]
