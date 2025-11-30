"""MCP type definitions and schemas."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class MCPErrorCode(str, Enum):
    """MCP error codes."""

    # Authentication errors
    UNAUTHORIZED = "UNAUTHORIZED"
    INVALID_TOKEN = "INVALID_TOKEN"

    # Request errors
    INVALID_REQUEST = "INVALID_REQUEST"
    INVALID_PARAMS = "INVALID_PARAMS"
    TOOL_NOT_FOUND = "TOOL_NOT_FOUND"

    # Execution errors
    EXECUTION_ERROR = "EXECUTION_ERROR"
    INSUFFICIENT_CREDITS = "INSUFFICIENT_CREDITS"
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    PERMISSION_DENIED = "PERMISSION_DENIED"

    # System errors
    INTERNAL_ERROR = "INTERNAL_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"


class MCPToolParameter(BaseModel):
    """Definition of a tool parameter."""

    name: str
    type: str  # "string", "integer", "number", "boolean", "array", "object"
    description: str
    required: bool = True
    default: Any = None
    enum: list[str] | None = None


class MCPToolDefinition(BaseModel):
    """Definition of an MCP tool."""

    name: str
    description: str
    parameters: list[MCPToolParameter] = Field(default_factory=list)
    category: str = "general"
    requires_auth: bool = True


class MCPRequest(BaseModel):
    """MCP tool execution request."""

    tool: str = Field(..., description="Name of the tool to execute")
    params: dict[str, Any] = Field(default_factory=dict, description="Tool parameters")
    request_id: str | None = Field(None, description="Optional request ID for tracking")


class MCPError(BaseModel):
    """MCP error response."""

    code: MCPErrorCode
    message: str
    details: dict[str, Any] | None = None


class MCPToolResult(BaseModel):
    """Result of a tool execution."""

    data: Any = None
    message: str | None = None


class MCPResponse(BaseModel):
    """MCP response wrapper."""

    status: str = Field(..., description="'success' or 'error'")
    result: MCPToolResult | None = None
    error: MCPError | None = None
    request_id: str | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    @classmethod
    def success(
        cls,
        data: Any = None,
        message: str | None = None,
        request_id: str | None = None,
    ) -> "MCPResponse":
        """Create a success response."""
        return cls(
            status="success",
            result=MCPToolResult(data=data, message=message),
            request_id=request_id,
        )

    @classmethod
    def from_error(
        cls,
        code: MCPErrorCode,
        message: str,
        details: dict[str, Any] | None = None,
        request_id: str | None = None,
    ) -> "MCPResponse":
        """Create an error response."""
        return cls(
            status="error",
            error=MCPError(code=code, message=message, details=details),
            request_id=request_id,
        )


class MCPListToolsResponse(BaseModel):
    """Response for listing available tools."""

    tools: list[MCPToolDefinition]
    total: int
