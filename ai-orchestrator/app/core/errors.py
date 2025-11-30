"""Error handling for AI Orchestrator.

This module provides custom exception classes and error handling utilities
for consistent error responses across the application.

Requirements: 需求 12.1, 12.2
"""

from typing import Any

import structlog
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.services.mcp_client import (
    InsufficientCreditsError,
    MCPConnectionError,
    MCPTimeoutError,
    MCPToolError,
)

logger = structlog.get_logger(__name__)


# Custom Exception Classes


class AIModelError(Exception):
    """Raised when AI model (Gemini) fails."""

    def __init__(
        self,
        message: str = "AI model error",
        code: str = "4001",
        details: dict[str, Any] | None = None,
    ):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(message)


class AIModelTimeoutError(AIModelError):
    """Raised when AI model request times out."""

    def __init__(self, message: str = "AI model request timed out"):
        super().__init__(message, code="4002")


class AIModelQuotaError(AIModelError):
    """Raised when AI model quota is exceeded."""

    def __init__(self, message: str = "AI model quota exceeded"):
        super().__init__(message, code="4003")


class GraphExecutionError(Exception):
    """Raised when LangGraph execution fails."""

    def __init__(
        self,
        message: str = "Graph execution error",
        code: str = "5001",
        details: dict[str, Any] | None = None,
    ):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(message)


class RetryableError(Exception):
    """Base class for errors that can be retried."""

    def __init__(
        self,
        message: str,
        code: str,
        max_retries: int = 3,
        retry_after: int | None = None,
    ):
        self.message = message
        self.code = code
        self.max_retries = max_retries
        self.retry_after = retry_after
        super().__init__(message)


# Error Response Format


def create_error_response(
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a consistent error response format.

    Args:
        code: Error code
        message: User-friendly error message
        details: Additional error details

    Returns:
        Error response dict
    """
    response = {
        "error": {
            "code": code,
            "message": message,
        }
    }

    if details:
        response["error"]["details"] = details

    return response


# Error Code to User Message Mapping (from INTERFACES.md)

ERROR_MESSAGES: dict[str, dict[str, Any]] = {
    # General Errors (1xxx)
    "1000": {
        "message": "发生未知错误，请稍后重试",
        "retryable": False,
        "action": "联系客服",
        "action_url": "/support",
    },
    "1001": {
        "message": "请求参数无效",
        "retryable": False,
        "action": None,
        "action_url": None,
    },
    "1002": {
        "message": "认证失败，请重新登录",
        "retryable": False,
        "action": "重新登录",
        "action_url": "/login",
    },
    "1003": {
        "message": "请求过于频繁，请稍后重试",
        "retryable": True,
        "action": "稍后重试",
        "action_url": None,
        "retry_after": 60,
    },
    # WebSocket Errors (2xxx)
    "2000": {
        "message": "连接失败，正在自动重连...",
        "retryable": True,
        "action": None,
        "action_url": None,
        "retry_after": 5,
    },
    "2003": {
        "message": "连接超时，请检查网络连接",
        "retryable": True,
        "action": "刷新页面",
        "action_url": None,
    },
    # MCP Errors (3xxx)
    "3000": {
        "message": "无法连接到数据服务，请稍后重试",
        "retryable": True,
        "action": "稍后重试",
        "action_url": None,
        "retry_after": 5,
    },
    "3001": {
        "message": "数据服务认证失败",
        "retryable": False,
        "action": "联系客服",
        "action_url": "/support",
    },
    "3002": {
        "message": "请求格式无效",
        "retryable": False,
        "action": None,
        "action_url": None,
    },
    "3003": {
        "message": "工具执行失败，请稍后重试",
        "retryable": True,
        "action": "重试",
        "action_url": None,
    },
    "3004": {
        "message": "请求超时，请稍后重试",
        "retryable": True,
        "action": "稍后重试",
        "action_url": None,
        "retry_after": 10,
    },
    # AI Model Errors (4xxx)
    "4000": {
        "message": "功能模块暂时不可用，请稍后重试",
        "retryable": True,
        "action": "稍后重试",
        "action_url": None,
    },
    "4001": {
        "message": "AI 服务暂时不可用，请稍后重试",
        "retryable": True,
        "action": "稍后重试",
        "action_url": None,
        "retry_after": 30,
    },
    "4002": {
        "message": "AI 请求超时，请稍后重试",
        "retryable": True,
        "action": "稍后重试",
        "action_url": None,
        "retry_after": 30,
    },
    "4003": {
        "message": "AI 服务配额已用尽，请稍后重试",
        "retryable": True,
        "action": "稍后重试",
        "action_url": None,
        "retry_after": 60,
    },
    # Data Errors (5xxx)
    "5000": {
        "message": "未找到相关数据，请检查输入",
        "retryable": False,
        "action": None,
        "action_url": None,
    },
    "5001": {
        "message": "处理请求时发生错误",
        "retryable": True,
        "action": "重试",
        "action_url": None,
    },
    "5002": {
        "message": "数据库错误，请稍后重试",
        "retryable": True,
        "action": "稍后重试",
        "action_url": None,
    },
    "5003": {
        "message": "文件上传失败，请检查网络连接后重试",
        "retryable": True,
        "action": "重试",
        "action_url": None,
    },
    # Business Errors (6xxx)
    "6000": {
        "message": "广告账户未绑定，请先绑定账户",
        "retryable": False,
        "action": "绑定账户",
        "action_url": "/settings/ad-accounts",
    },
    "6001": {
        "message": "广告账户授权已过期，请重新授权",
        "retryable": False,
        "action": "重新授权",
        "action_url": "/settings/ad-accounts",
    },
    "6011": {
        "message": "Credit 余额不足，请充值后继续使用",
        "retryable": False,
        "action": "前往充值",
        "action_url": "/billing/recharge",
    },
    "6012": {
        "message": "Credit 检查失败，请稍后重试",
        "retryable": True,
        "action": "重试",
        "action_url": None,
    },
    # Legacy keys for backward compatibility
    "VALIDATION_ERROR": {
        "message": "请求参数无效",
        "retryable": False,
        "action": None,
        "action_url": None,
    },
    "UNAUTHORIZED": {
        "message": "认证失败，请重新登录",
        "retryable": False,
        "action": "重新登录",
        "action_url": "/login",
    },
    "INVALID_TOKEN": {
        "message": "无效的认证令牌",
        "retryable": False,
        "action": "重新登录",
        "action_url": "/login",
    },
    "INTERNAL_ERROR": {
        "message": "服务器内部错误",
        "retryable": True,
        "action": "稍后重试",
        "action_url": None,
    },
    "UNKNOWN_ERROR": {
        "message": "发生未知错误，请稍后重试",
        "retryable": False,
        "action": "联系客服",
        "action_url": "/support",
    },
}


def get_user_message(code: str) -> str:
    """Get user-friendly message for error code."""
    error_info = ERROR_MESSAGES.get(code, ERROR_MESSAGES["UNKNOWN_ERROR"])
    return error_info["message"]


def get_error_info(code: str) -> dict[str, Any]:
    """Get full error info including retry and action details.

    Args:
        code: Error code

    Returns:
        Dict with message, retryable, action, action_url, retry_after
    """
    return ERROR_MESSAGES.get(code, ERROR_MESSAGES["UNKNOWN_ERROR"])


# Exception Handlers


async def mcp_connection_error_handler(
    request: Request,
    exc: MCPConnectionError,
) -> JSONResponse:
    """Handle MCP connection errors."""
    logger.error(
        "mcp_connection_error",
        error=str(exc),
        path=request.url.path,
    )

    error_info = get_error_info("3000")
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content=create_error_response(
            code="3000",
            message=error_info["message"],
            details={
                "retryable": error_info["retryable"],
                "retry_after": error_info.get("retry_after"),
                "action": error_info.get("action"),
                "action_url": error_info.get("action_url"),
            },
        ),
    )


async def mcp_timeout_error_handler(
    request: Request,
    exc: MCPTimeoutError,
) -> JSONResponse:
    """Handle MCP timeout errors."""
    logger.error(
        "mcp_timeout_error",
        error=str(exc),
        path=request.url.path,
    )

    error_info = get_error_info("3004")
    return JSONResponse(
        status_code=status.HTTP_504_GATEWAY_TIMEOUT,
        content=create_error_response(
            code="3004",
            message=error_info["message"],
            details={
                "retryable": error_info["retryable"],
                "retry_after": error_info.get("retry_after"),
                "action": error_info.get("action"),
            },
        ),
    )


async def mcp_tool_error_handler(
    request: Request,
    exc: MCPToolError,
) -> JSONResponse:
    """Handle MCP tool execution errors."""
    logger.error(
        "mcp_tool_error",
        error=str(exc),
        code=exc.code,
        path=request.url.path,
    )

    error_info = get_error_info(exc.code or "3003")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=create_error_response(
            code=exc.code or "3003",
            message=exc.message or error_info["message"],
            details={
                **exc.details,
                "retryable": error_info["retryable"],
                "action": error_info.get("action"),
            },
        ),
    )


async def insufficient_credits_error_handler(
    request: Request,
    exc: InsufficientCreditsError,
) -> JSONResponse:
    """Handle insufficient credits errors."""
    logger.warning(
        "insufficient_credits",
        required=exc.required,
        available=exc.available,
        path=request.url.path,
    )

    error_info = get_error_info("6011")
    return JSONResponse(
        status_code=status.HTTP_402_PAYMENT_REQUIRED,
        content=create_error_response(
            code="6011",
            message=error_info["message"],
            details={
                "required": exc.required,
                "available": exc.available,
                "action": error_info.get("action"),
                "action_url": error_info.get("action_url"),
            },
        ),
    )


async def ai_model_error_handler(
    request: Request,
    exc: AIModelError,
) -> JSONResponse:
    """Handle AI model errors."""
    logger.error(
        "ai_model_error",
        error=str(exc),
        code=exc.code,
        path=request.url.path,
    )

    error_info = get_error_info(exc.code)
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content=create_error_response(
            code=exc.code,
            message=error_info["message"],
            details={
                **exc.details,
                "retryable": error_info["retryable"],
                "retry_after": error_info.get("retry_after"),
                "action": error_info.get("action"),
            },
        ),
    )


async def validation_error_handler(
    request: Request,
    exc: ValidationError,
) -> JSONResponse:
    """Handle Pydantic validation errors."""
    logger.warning(
        "validation_error",
        errors=exc.errors(),
        path=request.url.path,
    )

    # Extract field errors
    field_errors = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"])
        field_errors.append(
            {
                "field": field,
                "message": error["msg"],
            }
        )

    error_info = get_error_info("VALIDATION_ERROR")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=create_error_response(
            code="VALIDATION_ERROR",
            message=error_info["message"],
            details={"fields": field_errors},
        ),
    )


async def graph_execution_error_handler(
    request: Request,
    exc: GraphExecutionError,
) -> JSONResponse:
    """Handle LangGraph execution errors."""
    logger.error(
        "graph_execution_error",
        error=str(exc),
        code=exc.code,
        path=request.url.path,
    )

    error_info = get_error_info(exc.code)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=create_error_response(
            code=exc.code,
            message=error_info["message"],
            details={
                **exc.details,
                "retryable": error_info["retryable"],
                "action": error_info.get("action"),
            },
        ),
    )


async def generic_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Handle any unhandled exceptions."""
    logger.error(
        "unhandled_exception",
        error=str(exc),
        error_type=type(exc).__name__,
        path=request.url.path,
        exc_info=True,
    )

    error_info = get_error_info("INTERNAL_ERROR")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=create_error_response(
            code="INTERNAL_ERROR",
            message=error_info["message"],
            details={
                "retryable": error_info["retryable"],
                "action": error_info.get("action"),
            },
        ),
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers with the FastAPI app.

    Args:
        app: FastAPI application instance
    """
    # MCP errors
    app.add_exception_handler(MCPConnectionError, mcp_connection_error_handler)
    app.add_exception_handler(MCPTimeoutError, mcp_timeout_error_handler)
    app.add_exception_handler(MCPToolError, mcp_tool_error_handler)
    app.add_exception_handler(InsufficientCreditsError, insufficient_credits_error_handler)

    # AI model errors
    app.add_exception_handler(AIModelError, ai_model_error_handler)
    app.add_exception_handler(AIModelTimeoutError, ai_model_error_handler)
    app.add_exception_handler(AIModelQuotaError, ai_model_error_handler)

    # Graph errors
    app.add_exception_handler(GraphExecutionError, graph_execution_error_handler)

    # Validation errors
    app.add_exception_handler(ValidationError, validation_error_handler)

    # Generic fallback
    app.add_exception_handler(Exception, generic_exception_handler)

    logger.info("exception_handlers_registered")


class ErrorHandler:
    """Centralized error handling utility class.

    Provides methods for handling errors within nodes and
    converting exceptions to state updates.

    Requirements: 需求 12.1, 12.2
    """

    @staticmethod
    def handle_error(
        error: Exception,
        context: str,
        user_id: str | None = None,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        """Handle an error and return state update dict.

        Args:
            error: The exception that occurred
            context: Context where error occurred (e.g., node name)
            user_id: Optional user ID for logging
            session_id: Optional session ID for logging

        Returns:
            Dict with error info suitable for AgentState update,
            including retry information and suggested actions.
        """
        log = logger.bind(
            context=context,
            user_id=user_id,
            session_id=session_id,
            error_type=type(error).__name__,
        )

        if isinstance(error, MCPConnectionError):
            log.error("mcp_connection_error", error=str(error))
            error_info = get_error_info("3000")
            return {
                "error": {
                    "code": "3000",
                    "type": "MCP_CONNECTION_FAILED",
                    "message": error_info["message"],
                    "retryable": error_info["retryable"],
                    "retry_after": error_info.get("retry_after"),
                    "action": error_info.get("action"),
                    "action_url": error_info.get("action_url"),
                }
            }

        elif isinstance(error, InsufficientCreditsError):
            log.warning("insufficient_credits", error=str(error))
            error_info = get_error_info("6011")
            return {
                "error": {
                    "code": "6011",
                    "type": "INSUFFICIENT_CREDITS",
                    "message": error_info["message"],
                    "details": {
                        "required": error.required,
                        "available": error.available,
                    },
                    "retryable": error_info["retryable"],
                    "action": error_info.get("action"),
                    "action_url": error_info.get("action_url"),
                }
            }

        elif isinstance(error, MCPTimeoutError):
            log.error("mcp_timeout", error=str(error))
            error_info = get_error_info("3004")
            return {
                "error": {
                    "code": "3004",
                    "type": "MCP_TIMEOUT",
                    "message": error_info["message"],
                    "retryable": error_info["retryable"],
                    "retry_after": error_info.get("retry_after"),
                    "action": error_info.get("action"),
                }
            }

        elif isinstance(error, MCPToolError):
            log.error("mcp_tool_error", error=str(error), code=error.code)
            error_info = get_error_info(error.code or "3003")
            return {
                "error": {
                    "code": error.code or "3003",
                    "type": "MCP_TOOL_ERROR",
                    "message": error.message or error_info["message"],
                    "details": error.details,
                    "retryable": error_info["retryable"],
                    "action": error_info.get("action"),
                }
            }

        elif isinstance(error, AIModelError):
            log.error("ai_model_error", error=str(error), code=error.code)
            error_info = get_error_info(error.code)
            return {
                "error": {
                    "code": error.code,
                    "type": "AI_MODEL_ERROR",
                    "message": error_info["message"],
                    "details": error.details,
                    "retryable": error_info["retryable"],
                    "retry_after": error_info.get("retry_after"),
                    "action": error_info.get("action"),
                }
            }

        elif isinstance(error, GraphExecutionError):
            log.error("graph_execution_error", error=str(error), code=error.code)
            error_info = get_error_info(error.code)
            return {
                "error": {
                    "code": error.code,
                    "type": "GRAPH_EXECUTION_ERROR",
                    "message": error_info["message"],
                    "details": error.details,
                    "retryable": error_info["retryable"],
                    "action": error_info.get("action"),
                }
            }

        else:
            log.error("unexpected_error", error=str(error), exc_info=True)
            error_info = get_error_info("1000")
            return {
                "error": {
                    "code": "1000",
                    "type": "UNKNOWN_ERROR",
                    "message": error_info["message"],
                    "retryable": error_info["retryable"],
                    "action": error_info.get("action"),
                    "action_url": error_info.get("action_url"),
                }
            }

    @staticmethod
    def is_retryable(error_info: dict[str, Any]) -> bool:
        """Check if an error is retryable.

        Args:
            error_info: Error dict from state

        Returns:
            True if the error can be retried
        """
        return error_info.get("retryable", False)

    @staticmethod
    def get_retry_after(error_info: dict[str, Any]) -> int | None:
        """Get the recommended retry delay in seconds.

        Args:
            error_info: Error dict from state

        Returns:
            Retry delay in seconds, or None if not specified
        """
        return error_info.get("retry_after")

    @staticmethod
    def get_suggested_action(error_info: dict[str, Any]) -> dict[str, str | None]:
        """Get the suggested action for the user.

        Args:
            error_info: Error dict from state

        Returns:
            Dict with action text and URL
        """
        return {
            "action": error_info.get("action"),
            "action_url": error_info.get("action_url"),
        }

    @staticmethod
    def create_node_error_state(
        error: Exception,
        node_name: str,
        partial_results: list[dict[str, Any]] | None = None,
        user_id: str | None = None,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        """Create an error state dict for node failures.

        This method is designed to be used in node try-except blocks
        to return a proper error state instead of raising exceptions.

        Args:
            error: The exception that occurred
            node_name: Name of the node where error occurred
            partial_results: Any partial results completed before failure
            user_id: Optional user ID for logging
            session_id: Optional session ID for logging

        Returns:
            Dict suitable for returning from a node function
        """
        error_state = ErrorHandler.handle_error(
            error=error,
            context=node_name,
            user_id=user_id,
            session_id=session_id,
        )

        # Preserve partial results if any
        if partial_results:
            error_state["completed_results"] = partial_results

        return error_state
