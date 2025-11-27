"""MCP (Model Context Protocol) Server module for AI Agent integration."""

# Import tools to register them with the registry
from app.mcp import tools  # noqa: F401
from app.mcp.registry import ToolRegistry
from app.mcp.server import MCPServer
from app.mcp.types import (
    MCPError,
    MCPRequest,
    MCPResponse,
    MCPToolDefinition,
    MCPToolResult,
)

__all__ = [
    "MCPServer",
    "ToolRegistry",
    "MCPRequest",
    "MCPResponse",
    "MCPError",
    "MCPToolDefinition",
    "MCPToolResult",
]
