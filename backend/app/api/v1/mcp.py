"""MCP API endpoints for AI Agent integration."""

from typing import Annotated

from fastapi import APIRouter, Header

from app.api.deps import DbSession
from app.mcp.auth import extract_token_from_header
from app.mcp.server import MCPServer
from app.mcp.types import (
    MCPListToolsResponse,
    MCPRequest,
    MCPResponse,
)

router = APIRouter(prefix="/mcp", tags=["MCP"])


@router.post("/v1/tools", response_model=MCPListToolsResponse)
async def list_tools(
    db: DbSession,
    category: str | None = None,
) -> MCPListToolsResponse:
    """List all available MCP tools.
    
    Returns a list of tool definitions including name, description,
    parameters, and category.
    
    Args:
        category: Optional filter by tool category
        
    Returns:
        List of available tools
    """
    server = MCPServer(db)
    return await server.list_tools(category=category)


@router.post("/v1/execute", response_model=MCPResponse)
async def execute_tool(
    request: MCPRequest,
    db: DbSession,
    authorization: Annotated[str | None, Header()] = None,
) -> MCPResponse:
    """Execute an MCP tool.
    
    Executes the specified tool with the provided parameters.
    Most tools require authentication via Bearer token.
    
    Args:
        request: Tool execution request with tool name and parameters
        authorization: Bearer token for authentication
        
    Returns:
        MCPResponse with result or error
    """
    token = extract_token_from_header(authorization)
    server = MCPServer(db)
    return await server.execute(request, token=token)


@router.get("/v1/tools/{tool_name}")
async def get_tool(
    tool_name: str,
    db: DbSession,
) -> dict:
    """Get details of a specific tool.
    
    Args:
        tool_name: Name of the tool
        
    Returns:
        Tool definition or error
    """
    server = MCPServer(db)
    tool_def = server.get_tool_definition(tool_name)

    if not tool_def:
        return {
            "status": "error",
            "error": {
                "code": "TOOL_NOT_FOUND",
                "message": f"Tool '{tool_name}' not found",
            }
        }

    return {
        "status": "success",
        "tool": tool_def.model_dump(),
    }


@router.get("/v1/categories")
async def get_categories(
    db: DbSession,
) -> dict:
    """Get all tool categories.
    
    Returns:
        List of category names
    """
    server = MCPServer(db)
    categories = server.get_categories()

    return {
        "status": "success",
        "categories": categories,
    }
