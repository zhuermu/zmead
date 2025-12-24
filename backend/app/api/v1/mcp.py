"""MCP API endpoints for AI Agent integration."""

from typing import Annotated

from fastapi import APIRouter, Header

from app.api.deps import DbSession
from app.mcp.auth import extract_token_from_header
from app.mcp.server import MCPServer
from app.mcp.types import (
    JSONRPCErrorResponse,
    JSONRPCRequest,
    JSONRPCResponse,
    JSONRPCSuccessResponse,
    MCPListToolsResponse,
    MCPRequest,
    MCPResponse,
)

router = APIRouter(prefix="/mcp", tags=["MCP"])


@router.post("/", response_model=JSONRPCResponse, include_in_schema=False)
@router.post("", response_model=JSONRPCResponse)
async def jsonrpc_handler(
    request: JSONRPCRequest,
    db: DbSession,
    authorization: Annotated[str | None, Header()] = None,
) -> JSONRPCResponse:
    """JSON-RPC 2.0 endpoint for standard MCP protocol.

    Supports methods:
    - tools/list: List all available tools
    - tools/call: Execute a tool
    """
    try:
        method = request.method
        params = request.params or {}
        request_id = request.id

        # Handle initialize method
        if method == "initialize":
            return JSONRPCSuccessResponse(
                id=request_id,
                result={
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {
                        "name": "AAE MCP Server",
                        "version": "1.0.0",
                    },
                    "capabilities": {
                        "tools": {},
                    },
                },
            )

        # Handle initialized notification (no response needed)
        elif method == "notifications/initialized":
            # This is a notification, no response needed
            return JSONRPCSuccessResponse(
                id=request_id,
                result={},
            )

        # Handle tools/list method
        elif method == "tools/list":
            server = MCPServer(db)
            tools_response = await server.list_tools()

            # Convert tools to standard MCP format with inputSchema
            mcp_tools = []
            for tool in tools_response.tools:
                # Build JSON Schema from parameters
                properties = {}
                required = []

                for param in tool.parameters:
                    param_schema = {
                        "type": param.type,
                        "description": param.description,
                    }

                    # Add enum if present
                    if param.enum:
                        param_schema["enum"] = param.enum

                    # Add default if present
                    if param.default is not None:
                        param_schema["default"] = param.default

                    properties[param.name] = param_schema

                    if param.required:
                        required.append(param.name)

                # Build inputSchema
                input_schema = {
                    "type": "object",
                    "properties": properties,
                }

                if required:
                    input_schema["required"] = required

                mcp_tools.append({
                    "name": tool.name,
                    "description": tool.description,
                    "inputSchema": input_schema,
                })

            return JSONRPCSuccessResponse(
                id=request_id,
                result={
                    "tools": mcp_tools,
                },
            )

        # Handle tools/call method
        elif method == "tools/call":
            tool_name = params.get("name")
            tool_params = params.get("arguments", {})

            if not tool_name:
                from app.mcp.types import JSONRPCError
                return JSONRPCErrorResponse(
                    id=request_id,
                    error=JSONRPCError(
                        code=-32602,
                        message="Invalid params: 'name' is required",
                    ),
                )

            # Convert to MCP request format
            mcp_request = MCPRequest(
                tool=tool_name,
                params=tool_params,
                request_id=str(request_id) if request_id else None,
            )

            # Execute via MCP server
            token = extract_token_from_header(authorization)
            server = MCPServer(db)
            mcp_response = await server.execute(mcp_request, token=token)

            # Convert MCP response to JSON-RPC response
            if mcp_response.status == "success":
                return JSONRPCSuccessResponse(
                    id=request_id,
                    result=mcp_response.result.data if mcp_response.result else None,
                )
            else:
                from app.mcp.types import JSONRPCError
                error_code = -32000  # Server error
                if mcp_response.error:
                    error_message = mcp_response.error.message
                    error_data = mcp_response.error.details
                else:
                    error_message = "Unknown error"
                    error_data = None

                return JSONRPCErrorResponse(
                    id=request_id,
                    error=JSONRPCError(
                        code=error_code,
                        message=error_message,
                        data=error_data,
                    ),
                )

        # Method not found
        else:
            from app.mcp.types import JSONRPCError
            return JSONRPCErrorResponse(
                id=request_id,
                error=JSONRPCError(
                    code=-32601,
                    message=f"Method not found: {method}",
                ),
            )

    except Exception as e:
        from app.mcp.types import JSONRPCError
        return JSONRPCErrorResponse(
            id=request.id,
            error=JSONRPCError(
                code=-32603,
                message=f"Internal error: {str(e)}",
            ),
        )


@router.get("/", include_in_schema=False)
@router.get("")
async def mcp_info() -> dict:
    """MCP server information and capabilities.

    This endpoint provides server information for MCP protocol discovery.
    Supports both with and without trailing slash.
    """
    return {
        "name": "AAE MCP Server",
        "version": "1.0.0",
        "protocol": "mcp",
        "capabilities": {
            "tools": True,
            "execute": True,
        },
        "endpoints": {
            "tools": "/api/v1/mcp/tools",
            "execute": "/api/v1/mcp/execute",
            "categories": "/api/v1/mcp/categories",
            "jsonrpc": "/api/v1/mcp",
        },
    }


@router.post("/tools", response_model=MCPListToolsResponse)
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


@router.post("/execute", response_model=MCPResponse)
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


@router.get("/tools/{tool_name}")
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


@router.get("/categories")
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
