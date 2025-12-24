"""MCP Client for communicating with Web Platform.

This module provides the MCPClient class for making tool calls to the
Web Platform's MCP Server. It includes:
- HTTP client with connection pooling
- Exponential backoff retry logic
- Request/response logging
- Timeout handling
- Custom exceptions for error handling
"""

import asyncio
import uuid
from datetime import datetime
from typing import Any

import httpx
import structlog

from app.core.config import get_settings

logger = structlog.get_logger(__name__)


# Custom Exceptions
class MCPError(Exception):
    """Base exception for MCP errors."""

    def __init__(
        self,
        message: str,
        code: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}


class MCPConnectionError(MCPError):
    """Raised when connection to MCP server fails."""

    def __init__(self, message: str = "Failed to connect to MCP server"):
        super().__init__(message, code="3000")


class MCPToolError(MCPError):
    """Raised when MCP tool execution fails."""

    def __init__(
        self,
        message: str,
        code: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message, code=code or "3003", details=details)


class InsufficientCreditsError(MCPError):
    """Raised when user has insufficient credits."""

    def __init__(
        self,
        message: str = "Insufficient credits",
        required: str | None = None,
        available: str | None = None,
    ):
        details = {}
        if required:
            details["required"] = required
        if available:
            details["available"] = available
        super().__init__(message, code="6011", details=details)
        self.required = required
        self.available = available


class MCPTimeoutError(MCPError):
    """Raised when MCP request times out."""

    def __init__(self, message: str = "MCP request timed out"):
        super().__init__(message, code="3004")


# Error code to user-friendly message mapping
ERROR_MESSAGES = {
    "UNAUTHORIZED": "认证失败，请重新登录",
    "INVALID_TOKEN": "无效的认证令牌",
    "INVALID_REQUEST": "请求格式无效",
    "INVALID_PARAMS": "参数无效",
    "TOOL_NOT_FOUND": "工具不存在",
    "EXECUTION_ERROR": "执行失败，请稍后重试",
    "INSUFFICIENT_CREDITS": "Credit 余额不足，请充值后继续使用",
    "RESOURCE_NOT_FOUND": "资源未找到",
    "PERMISSION_DENIED": "权限不足",
    "INTERNAL_ERROR": "服务器内部错误",
    "SERVICE_UNAVAILABLE": "服务暂时不可用",
}


def get_user_friendly_message(code: str) -> str:
    """Get user-friendly error message for error code."""
    return ERROR_MESSAGES.get(code, "发生未知错误，请稍后重试")


class MCPClient:
    """Client for communicating with Web Platform MCP Server.

    Features:
    - Connection pooling via httpx.AsyncClient
    - Exponential backoff retry (1s, 2s, 4s, max 3 retries)
    - Request/response logging with structlog
    - Timeout handling (default 30s)
    - Service token authentication

    Example:
        async with MCPClient() as client:
            result = await client.call_tool("check_credit", {"amount": 10})
    """

    def __init__(
        self,
        base_url: str | None = None,
        service_token: str | None = None,
        timeout: float = 30.0,
        max_retries: int = 3,
        backoff_base: float = 1.0,
        backoff_factor: float = 2.0,
    ):
        """Initialize MCP Client.

        Args:
            base_url: Web Platform URL. Defaults to settings.web_platform_url
            service_token: Service token for auth. Defaults to settings value
            timeout: Request timeout in seconds (default 30s)
            max_retries: Maximum retry attempts (default 3)
            backoff_base: Base wait time for retries in seconds (default 1s)
            backoff_factor: Multiplier for exponential backoff (default 2.0)
        """
        settings = get_settings()

        self.base_url = base_url or settings.web_platform_url
        self.service_token = service_token or settings.web_platform_service_token
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self.backoff_factor = backoff_factor

        # MCP endpoint (JSON-RPC 2.0)
        self.mcp_endpoint = f"{self.base_url}/api/v1/mcp"

        # Request counter for JSON-RPC IDs
        self._request_counter = 0

        # HTTP client (created on first use or context manager entry)
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client with connection pooling."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                limits=httpx.Limits(
                    max_keepalive_connections=20,
                    max_connections=100,
                ),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.service_token}",
                    "User-Agent": "AI-Orchestrator/1.0",
                },
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> "MCPClient":
        """Async context manager entry."""
        await self._get_client()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()

    async def call_tool(
        self,
        tool_name: str,
        parameters: dict[str, Any] | None = None,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        """Call an MCP tool with retry logic using JSON-RPC 2.0 protocol.

        Args:
            tool_name: Name of the MCP tool to call
            parameters: Tool parameters
            request_id: Optional request ID for tracing (used for logging only)

        Returns:
            Tool result data

        Raises:
            MCPConnectionError: Connection to MCP server failed
            MCPToolError: Tool execution failed
            InsufficientCreditsError: User has insufficient credits
            MCPTimeoutError: Request timed out
        """
        if request_id is None:
            request_id = str(uuid.uuid4())[:8]

        if parameters is None:
            parameters = {}

        # Generate JSON-RPC ID
        self._request_counter += 1
        jsonrpc_id = self._request_counter

        # Build JSON-RPC 2.0 request
        request_payload = {
            "jsonrpc": "2.0",
            "id": jsonrpc_id,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": parameters,
            },
        }

        log = logger.bind(
            tool=tool_name,
            request_id=request_id,
        )

        log.info("mcp_call_start", params=parameters)
        start_time = datetime.utcnow()

        last_error: Exception | None = None

        for attempt in range(self.max_retries):
            try:
                result = await self._execute_request(
                    request_payload,
                    log,
                    attempt,
                )

                duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
                log.info(
                    "mcp_call_success",
                    duration_ms=round(duration_ms, 2),
                    attempt=attempt + 1,
                )

                return result

            except (MCPConnectionError, MCPTimeoutError) as e:
                last_error = e

                if attempt < self.max_retries - 1:
                    wait_time = self.backoff_base * (self.backoff_factor**attempt)
                    log.warning(
                        "mcp_call_retry",
                        attempt=attempt + 1,
                        max_retries=self.max_retries,
                        wait_seconds=wait_time,
                        error=str(e),
                    )
                    await asyncio.sleep(wait_time)
                else:
                    log.error(
                        "mcp_call_failed",
                        attempt=attempt + 1,
                        error=str(e),
                    )
                    raise

            except (MCPToolError, InsufficientCreditsError):
                # Don't retry tool errors or credit errors
                raise

        # Should not reach here, but just in case
        if last_error:
            raise last_error
        raise MCPConnectionError("Unknown error during MCP call")

    async def _execute_request(
        self,
        payload: dict[str, Any],
        log: Any,
        attempt: int,
    ) -> dict[str, Any]:
        """Execute a single MCP request using JSON-RPC 2.0 protocol.

        Args:
            payload: JSON-RPC 2.0 request payload
            log: Bound logger
            attempt: Current attempt number

        Returns:
            Tool result data

        Raises:
            MCPConnectionError: Connection failed
            MCPTimeoutError: Request timed out
            MCPToolError: Tool execution failed
            InsufficientCreditsError: Insufficient credits
        """
        client = await self._get_client()

        try:
            response = await client.post(
                self.mcp_endpoint,
                json=payload,
            )

            log.debug(
                "mcp_response_received",
                status_code=response.status_code,
                attempt=attempt + 1,
            )

            # Handle HTTP errors
            if response.status_code >= 500:
                raise MCPConnectionError(f"MCP server error: HTTP {response.status_code}")

            if response.status_code == 401:
                raise MCPToolError(
                    "Authentication failed",
                    code="UNAUTHORIZED",
                )

            if response.status_code == 403:
                raise MCPToolError(
                    "Permission denied",
                    code="PERMISSION_DENIED",
                )

            # Parse JSON-RPC 2.0 response
            try:
                data = response.json()
            except Exception as e:
                raise MCPToolError(
                    f"Invalid response format: {e}",
                    code="INVALID_RESPONSE",
                )

            # Check for JSON-RPC error
            if "error" in data and data["error"] is not None:
                error = data["error"]
                error_code = error.get("code", -32000)
                error_message = error.get("message", "Unknown error")
                error_data = error.get("data")

                # Map JSON-RPC error codes to MCP error codes
                if error_code == -32601:
                    mcp_code = "TOOL_NOT_FOUND"
                elif error_code == -32602:
                    mcp_code = "INVALID_PARAMS"
                elif error_code == -32000:
                    # Server error - parse from message or data
                    mcp_code = "EXECUTION_ERROR"
                    if error_data and isinstance(error_data, dict):
                        mcp_code = error_data.get("code", "EXECUTION_ERROR")
                else:
                    mcp_code = "INTERNAL_ERROR"

                # Check for insufficient credits
                if "INSUFFICIENT_CREDITS" in str(error_message) or mcp_code == "INSUFFICIENT_CREDITS":
                    raise InsufficientCreditsError(
                        message=get_user_friendly_message("INSUFFICIENT_CREDITS"),
                        required=error_data.get("required") if error_data else None,
                        available=error_data.get("available") if error_data else None,
                    )

                raise MCPToolError(
                    message=get_user_friendly_message(mcp_code),
                    code=mcp_code,
                    details=error_data if isinstance(error_data, dict) else None,
                )

            # Success - return result
            if "result" in data:
                return data["result"]

            # No result or error
            raise MCPToolError(
                "Invalid JSON-RPC response: missing result and error",
                code="INVALID_RESPONSE",
            )

        except httpx.TimeoutException as e:
            raise MCPTimeoutError(f"Request timed out: {e}")

        except httpx.ConnectError as e:
            raise MCPConnectionError(f"Connection failed: {e}")

        except httpx.HTTPError as e:
            raise MCPConnectionError(f"HTTP error: {e}")

    # =========================================================================
    # Credit Management Wrappers (Task 2.3)
    # =========================================================================

    async def check_credit(
        self,
        user_id: str,
        estimated_credits: float,
        operation_type: str,
    ) -> dict[str, Any]:
        """Check if user has sufficient credits for an operation.

        Args:
            user_id: User ID
            estimated_credits: Estimated credits required
            operation_type: Type of operation (e.g., "image_generation")

        Returns:
            Dict with 'sufficient', 'required', 'available' keys

        Raises:
            InsufficientCreditsError: If user doesn't have enough credits
            MCPError: If check fails
        """
        log = logger.bind(
            user_id=user_id,
            operation_type=operation_type,
            estimated_credits=estimated_credits,
        )
        log.info("credit_check_start")

        result = await self.call_tool(
            "check_credit",
            {
                "amount": estimated_credits,
            },
        )

        sufficient = result.get("sufficient", False)

        log.info(
            "credit_check_complete",
            sufficient=sufficient,
            available=result.get("available"),
        )

        if not sufficient:
            raise InsufficientCreditsError(
                message="Credit 余额不足，请充值后继续使用",
                required=str(estimated_credits),
                available=result.get("available"),
            )

        return result

    async def deduct_credit(
        self,
        user_id: str,
        credits: float,
        operation_type: str,
        operation_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Deduct credits from user's balance.

        Args:
            user_id: User ID
            credits: Amount of credits to deduct
            operation_type: Type of operation
            operation_id: Unique operation ID for tracking/refunds
            details: Additional details (model, tokens, etc.)

        Returns:
            Transaction details including transaction_id, balance_after

        Raises:
            InsufficientCreditsError: If user doesn't have enough credits
            MCPError: If deduction fails
        """
        log = logger.bind(
            user_id=user_id,
            operation_type=operation_type,
            credits=credits,
            operation_id=operation_id,
        )
        log.info("credit_deduct_start")

        params: dict[str, Any] = {
            "amount": credits,
            "operation_type": operation_type,
        }

        if operation_id:
            params["operation_id"] = operation_id
        if details:
            params["details"] = details

        result = await self.call_tool("deduct_credit", params)

        log.info(
            "credit_deduct_complete",
            transaction_id=result.get("transaction_id"),
            balance_after=result.get("balance_after"),
        )

        return result

    async def refund_credit(
        self,
        user_id: str,
        credits: float,
        operation_type: str,
        operation_id: str | None = None,
        reason: str | None = None,
    ) -> dict[str, Any]:
        """Refund credits to user's balance.

        Args:
            user_id: User ID
            credits: Amount of credits to refund
            operation_type: Type of operation being refunded
            operation_id: Original operation ID
            reason: Reason for the refund

        Returns:
            Transaction details including transaction_id, balance_after

        Raises:
            MCPError: If refund fails
        """
        log = logger.bind(
            user_id=user_id,
            operation_type=operation_type,
            credits=credits,
            operation_id=operation_id,
            reason=reason,
        )
        log.info("credit_refund_start")

        params: dict[str, Any] = {
            "amount": credits,
            "operation_type": operation_type,
        }

        if operation_id:
            params["operation_id"] = operation_id
        if reason:
            params["reason"] = reason

        result = await self.call_tool("refund_credit", params)

        log.info(
            "credit_refund_complete",
            transaction_id=result.get("transaction_id"),
            balance_after=result.get("balance_after"),
        )

        return result

    async def get_credit_balance(self, user_id: str) -> dict[str, Any]:
        """Get user's current credit balance.

        Args:
            user_id: User ID

        Returns:
            Balance info with gifted_credits, purchased_credits, total_credits
        """
        return await self.call_tool("get_credit_balance", {})

    # =========================================================================
    # Conversation Persistence Wrappers (Task 2.4)
    # =========================================================================

    async def save_conversation(
        self,
        user_id: str,
        session_id: str,
        messages: list[dict[str, Any]],
        title: str | None = None,
        current_intent: str | None = None,
        context_data: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """Save conversation messages to Web Platform.

        Handles persistence failures gracefully - logs error but doesn't fail.

        Args:
            user_id: User ID
            session_id: Session ID for the conversation
            messages: List of message dicts with role, content, timestamp
            title: Optional conversation title
            current_intent: Current recognized intent
            context_data: Additional context data

        Returns:
            Save result or None if failed
        """
        log = logger.bind(
            user_id=user_id,
            session_id=session_id,
            message_count=len(messages),
        )
        log.info("conversation_save_start")

        params: dict[str, Any] = {
            "session_id": session_id,
            "messages": messages,
        }

        if title:
            params["title"] = title
        if current_intent:
            params["current_intent"] = current_intent
        if context_data:
            params["context_data"] = context_data

        # Retry logic for transient failures
        for attempt in range(self.max_retries):
            try:
                result = await self.call_tool("save_conversation", params)

                log.info(
                    "conversation_save_complete",
                    conversation_id=result.get("conversation_id"),
                    messages_saved=result.get("messages_saved"),
                )

                return result

            except (MCPConnectionError, MCPTimeoutError) as e:
                if attempt < self.max_retries - 1:
                    wait_time = self.backoff_base * (self.backoff_factor**attempt)
                    log.warning(
                        "conversation_save_retry",
                        attempt=attempt + 1,
                        error=str(e),
                        wait_seconds=wait_time,
                    )
                    await asyncio.sleep(wait_time)
                else:
                    # Log error but don't fail the request
                    log.error(
                        "conversation_save_failed",
                        error=str(e),
                    )
                    return None

            except MCPError as e:
                # Log error but don't fail the request
                log.error(
                    "conversation_save_failed",
                    error=str(e),
                    code=e.code,
                )
                return None

        return None

    async def get_conversation_history(
        self,
        user_id: str,
        session_id: str,
        limit: int = 50,
        before_id: int | None = None,
    ) -> dict[str, Any] | None:
        """Get conversation history from Web Platform.

        Handles failures gracefully - logs error but doesn't fail.

        Args:
            user_id: User ID
            session_id: Session ID for the conversation
            limit: Maximum messages to return (default 50, max 200)
            before_id: Get messages before this ID (for pagination)

        Returns:
            Conversation history or None if failed
        """
        log = logger.bind(
            user_id=user_id,
            session_id=session_id,
            limit=limit,
        )
        log.info("conversation_history_start")

        params: dict[str, Any] = {
            "session_id": session_id,
            "limit": min(limit, 200),
        }

        if before_id:
            params["before_id"] = before_id

        # Retry logic for transient failures
        for attempt in range(self.max_retries):
            try:
                result = await self.call_tool("get_conversation_history", params)

                log.info(
                    "conversation_history_complete",
                    message_count=result.get("total", 0),
                    has_more=result.get("has_more", False),
                )

                return result

            except (MCPConnectionError, MCPTimeoutError) as e:
                if attempt < self.max_retries - 1:
                    wait_time = self.backoff_base * (self.backoff_factor**attempt)
                    log.warning(
                        "conversation_history_retry",
                        attempt=attempt + 1,
                        error=str(e),
                        wait_seconds=wait_time,
                    )
                    await asyncio.sleep(wait_time)
                else:
                    log.error(
                        "conversation_history_failed",
                        error=str(e),
                    )
                    return None

            except MCPError as e:
                log.error(
                    "conversation_history_failed",
                    error=str(e),
                    code=e.code,
                )
                return None

        return None

    async def list_conversations(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any] | None:
        """List user's conversations.

        Args:
            user_id: User ID
            page: Page number (1-indexed)
            page_size: Items per page (max 50)

        Returns:
            List of conversations or None if failed
        """
        try:
            return await self.call_tool(
                "list_conversations",
                {
                    "page": page,
                    "page_size": min(page_size, 50),
                },
            )
        except MCPError as e:
            logger.error(
                "list_conversations_failed",
                user_id=user_id,
                error=str(e),
            )
            return None
