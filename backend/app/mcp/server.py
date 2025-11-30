"""MCP Server implementation."""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.mcp.auth import MCPAuthError, authenticate_mcp_request
from app.mcp.registry import ToolRegistry
from app.mcp.types import (
    MCPErrorCode,
    MCPListToolsResponse,
    MCPRequest,
    MCPResponse,
    MCPToolDefinition,
)
from app.mcp.validation import ValidationError, validate_request_params
from app.models.user import User
from app.services.credit import InsufficientCreditsError

logger = logging.getLogger(__name__)


class MCPServer:
    """MCP Server for handling tool requests from AI Agents.
    
    The MCP Server provides:
    - Tool discovery (list available tools)
    - Tool execution with authentication
    - Request validation
    - Response formatting
    """

    def __init__(self, db: AsyncSession):
        """Initialize MCP Server.
        
        Args:
            db: Database session for tool operations
        """
        self.db = db
        self.registry = ToolRegistry()

    async def list_tools(
        self,
        category: str | None = None,
    ) -> MCPListToolsResponse:
        """List all available MCP tools.
        
        Args:
            category: Optional category filter
            
        Returns:
            MCPListToolsResponse with tool definitions
        """
        tools = self.registry.list_tools(category=category)
        return MCPListToolsResponse(tools=tools, total=len(tools))

    async def execute(
        self,
        request: MCPRequest,
        token: str | None = None,
    ) -> MCPResponse:
        """Execute an MCP tool.
        
        Args:
            request: Tool execution request
            token: Authentication token
            
        Returns:
            MCPResponse with result or error
        """
        request_id = request.request_id

        try:
            # Get tool definition
            tool_def = self.registry.get_tool(request.tool)
            if not tool_def:
                return MCPResponse.from_error(
                    code=MCPErrorCode.TOOL_NOT_FOUND,
                    message=f"Tool '{request.tool}' not found",
                    request_id=request_id,
                )

            # Authenticate if required
            user: User | None = None
            if tool_def.requires_auth:
                try:
                    user = await authenticate_mcp_request(token, self.db)
                except MCPAuthError as e:
                    return MCPResponse.from_error(
                        code=MCPErrorCode.UNAUTHORIZED,
                        message=str(e),
                        request_id=request_id,
                    )

            # Validate parameters
            try:
                validated_params = validate_request_params(
                    request.params,
                    tool_def,
                )
            except ValidationError as e:
                return MCPResponse.from_error(
                    code=e.code,
                    message=e.message,
                    details=e.details,
                    request_id=request_id,
                )

            # Get handler
            handler = self.registry.get_handler(request.tool)
            if not handler:
                return MCPResponse.from_error(
                    code=MCPErrorCode.INTERNAL_ERROR,
                    message="Tool handler not found",
                    request_id=request_id,
                )

            # Execute tool
            try:
                # Pass user_id and db to handler along with validated params
                if user:
                    result = await handler(
                        user_id=user.id,
                        db=self.db,
                        **validated_params,
                    )
                else:
                    result = await handler(
                        db=self.db,
                        **validated_params,
                    )

                return MCPResponse.success(
                    data=result,
                    request_id=request_id,
                )

            except InsufficientCreditsError as e:
                return MCPResponse.from_error(
                    code=MCPErrorCode.INSUFFICIENT_CREDITS,
                    message=str(e),
                    details={
                        "error_code": e.error_code,
                        "required": str(e.required),
                        "available": str(e.available),
                    },
                    request_id=request_id,
                )
            except PermissionError as e:
                return MCPResponse.from_error(
                    code=MCPErrorCode.PERMISSION_DENIED,
                    message=str(e),
                    request_id=request_id,
                )
            except ValueError as e:
                return MCPResponse.from_error(
                    code=MCPErrorCode.INVALID_PARAMS,
                    message=str(e),
                    request_id=request_id,
                )
            except Exception as e:
                logger.exception(f"Tool execution error: {request.tool}")
                return MCPResponse.from_error(
                    code=MCPErrorCode.EXECUTION_ERROR,
                    message=f"Tool execution failed: {str(e)}",
                    request_id=request_id,
                )

        except Exception:
            logger.exception("MCP server error")
            return MCPResponse.from_error(
                code=MCPErrorCode.INTERNAL_ERROR,
                message="Internal server error",
                request_id=request_id,
            )

    def get_tool_definition(self, name: str) -> MCPToolDefinition | None:
        """Get a specific tool definition.
        
        Args:
            name: Tool name
            
        Returns:
            Tool definition or None
        """
        return self.registry.get_tool(name)

    def get_categories(self) -> list[str]:
        """Get all tool categories.
        
        Returns:
            List of category names
        """
        return self.registry.get_categories()
