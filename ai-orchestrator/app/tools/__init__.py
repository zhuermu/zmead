"""Tools module for ReAct Agent.

This module provides the tools architecture for the ReAct Agent, supporting
three types of tools:
1. LangChain built-in tools (google_search, calculator, etc.)
2. Agent custom tools (can call LLMs for AI capabilities)
3. MCP Server tools (backend API calls via MCP protocol)
"""

from app.tools.base import AgentTool, ToolCategory, ToolMetadata, ToolParameter
from app.tools.registry import ToolRegistry, get_tool_registry, reset_tool_registry
from app.tools.campaign_tools import create_campaign_tools
from app.tools.creative_tools import create_creative_tools
from app.tools.landing_page_tools import create_landing_page_tools
from app.tools.langchain_tools import create_langchain_tools
from app.tools.market_tools import create_market_tools
from app.tools.mcp_tools import create_mcp_tools
from app.tools.performance_tools import create_performance_tools

__all__ = [
    # Base classes
    "AgentTool",
    "ToolCategory",
    "ToolMetadata",
    "ToolParameter",
    # Registry
    "ToolRegistry",
    "get_tool_registry",
    "reset_tool_registry",
    # Tool factories
    "create_campaign_tools",
    "create_creative_tools",
    "create_landing_page_tools",
    "create_langchain_tools",
    "create_market_tools",
    "create_mcp_tools",
    "create_performance_tools",
]
