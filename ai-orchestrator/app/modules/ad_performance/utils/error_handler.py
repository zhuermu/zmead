"""
Error handling utilities for Ad Performance module.

This module provides specialized error handling for ad platform APIs,
MCP calls, and AI model interactions specific to the Ad Performance module.

Requirements: 8.5
"""

import asyncio
from typing import Any

import structlog

from app.core.errors import (
    AIModelError,
    AIModelTimeoutError,
    AIModelQuotaError,
    RetryableError,
    get_error_info,
)
from app.services.mcp_client import (
    MCPConnectionError,
    MCPTimeoutError,
    MCPToolError,
    InsufficientCreditsError,
)
from app.services.gemini_client import GeminiError

logger = structlog.get_logger(__name__)


# Ad Platform API Errors


class AdPlatformError(Exception):
    """Base class for ad platform API errors."""

    def __init__(
        self,
        message: str,
        platform: str,
        code: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        self.message = message
        self.platform = platform
        self.code = code
        self.details = details or {}
        super().__init__(message)


class TokenExpiredError(AdPlatformError):
    """Raised when ad platform token has expired."""

    def __init__(self, platform: str, message: str = "Token expired"):
        super().__init__(
            message=message,
            platform=platform,
            code="6001",
        )


class TokenInvalidError(AdPlatformError):
    """Raised when ad platform token is invalid."""

    def __init__(self, platform: str, message: str = "Invalid token"):
        super().__init__(
            message=message,
            platform=platform,
            code="6001",
        )


class PermissionDeniedError(AdPlatformError):
    """Raised when access to ad platform resource is denied."""

    def __init__(self, platform: str, message: str = "Permission denied"):
        super().__init__(
            message=message,
            platform=platform,
            code="6001",
        )


class RateLimitError(AdPlatformError):
    """Raised when ad platform rate limit is exceeded."""

    def __init__(
        self,
        platform: str,
        retry_after: int = 60,
        message: str = "Rate limit exceeded",
    ):
        super().__init__(
            message=message,
            platform=platform,
            code="1003",
            details={"retry_after": retry_after},
        )
        self.retry_after = retry_after


class PlatformServiceError(AdPlatformError):
    """Raised when ad platform service returns 5xx error."""

    def __init__(
        self,
        platform: str,
        status_code: int,
        message: str = "Platform service error",
    ):
        super().__init__(
            message=message,
            platform=platform,
            code="4002",
            details={"status_code": status_code},
        )


class PlatformTimeoutError(AdPlatformError):
    """Raised when ad platform API request times out."""

    def __init__(self, platform: str, message: str = "Request timeout"):
        super().__init__(
            message=message,
            platform=platform,
            code="4002",
        )


# Error Handler Class


class AdPerformanceErrorHandler:
    """
    Centralized error handling for Ad Performance module.

    Handles errors from:
    - Ad platform APIs (Meta, TikTok, Google)
    - MCP client calls
    - AI model (Gemini) calls
    - Data validation

    Returns standardized error responses with retry information.

    Requirements: 8.5
    """

    @staticmethod
    def handle_api_error(
        error: Exception,
        platform: str,
        retry_count: int = 0,
    ) -> dict[str, Any]:
        """
        Handle ad platform API errors.

        Args:
            error: The exception that occurred
            platform: Platform name (meta, tiktok, google)
            retry_count: Current retry attempt number

        Returns:
            Standardized error response dict with:
            - status: "error"
            - error_code: Error code from INTERFACES.md
            - message: User-friendly message
            - retry_allowed: Whether retry is allowed
            - retry_after: Seconds to wait before retry (if applicable)
            - platform: Platform name
        """
        log = logger.bind(
            platform=platform,
            retry_count=retry_count,
            error_type=type(error).__name__,
        )

        # Token expired or invalid (401/403)
        if isinstance(error, (TokenExpiredError, TokenInvalidError, PermissionDeniedError)):
            log.warning("token_error", error=str(error))
            error_info = get_error_info("6001")
            return {
                "status": "error",
                "error_code": "6001",
                "message": error_info["message"],
                "retry_allowed": False,
                "action": error_info.get("action"),
                "action_url": error_info.get("action_url"),
                "platform": platform,
            }

        # Rate limit exceeded (429)
        elif isinstance(error, RateLimitError):
            log.warning("rate_limit_error", retry_after=error.retry_after)
            error_info = get_error_info("1003")
            return {
                "status": "error",
                "error_code": "1003",
                "message": error_info["message"],
                "retry_allowed": True,
                "retry_after": error.retry_after,
                "platform": platform,
            }

        # Platform service error (500)
        elif isinstance(error, PlatformServiceError):
            log.error("platform_service_error", status_code=error.details.get("status_code"))
            if retry_count < 3:
                return {
                    "status": "error",
                    "error_code": "4002",
                    "message": "Platform service temporarily unavailable",
                    "retry_allowed": True,
                    "retry_after": 2 ** retry_count,  # Exponential backoff
                    "platform": platform,
                }
            else:
                error_info = get_error_info("4002")
                return {
                    "status": "error",
                    "error_code": "4002",
                    "message": error_info["message"],
                    "retry_allowed": False,
                    "platform": platform,
                }

        # Timeout error
        elif isinstance(error, PlatformTimeoutError):
            log.error("platform_timeout_error")
            if retry_count < 3:
                return {
                    "status": "error",
                    "error_code": "4002",
                    "message": "Request timeout, retrying...",
                    "retry_allowed": True,
                    "retry_after": 2 ** retry_count,
                    "platform": platform,
                }
            else:
                error_info = get_error_info("4002")
                return {
                    "status": "error",
                    "error_code": "4002",
                    "message": error_info["message"],
                    "retry_allowed": False,
                    "platform": platform,
                }

        # Generic ad platform error
        elif isinstance(error, AdPlatformError):
            log.error("ad_platform_error", error=str(error), code=error.code)
            error_info = get_error_info(error.code or "4002")
            return {
                "status": "error",
                "error_code": error.code or "4002",
                "message": error_info["message"],
                "retry_allowed": retry_count < 3,
                "retry_after": 2 ** retry_count if retry_count < 3 else None,
                "platform": platform,
            }

        # Unknown error
        else:
            log.error("unknown_api_error", error=str(error), exc_info=True)
            if retry_count < 3:
                return {
                    "status": "error",
                    "error_code": "4002",
                    "message": "API call failed, retrying...",
                    "retry_allowed": True,
                    "retry_after": 2 ** retry_count,
                    "platform": platform,
                }
            else:
                error_info = get_error_info("4002")
                return {
                    "status": "error",
                    "error_code": "4002",
                    "message": error_info["message"],
                    "retry_allowed": False,
                    "platform": platform,
                }

    @staticmethod
    def handle_mcp_error(error: Exception) -> dict[str, Any]:
        """
        Handle MCP client errors.

        Args:
            error: The MCP exception that occurred

        Returns:
            Standardized error response dict
        """
        log = logger.bind(error_type=type(error).__name__)

        # Connection error
        if isinstance(error, MCPConnectionError):
            log.error("mcp_connection_error", error=str(error))
            error_info = get_error_info("3000")
            return {
                "status": "error",
                "error_code": "3000",
                "message": error_info["message"],
                "retry_allowed": True,
                "retry_after": error_info.get("retry_after"),
                "action": error_info.get("action"),
            }

        # Timeout error
        elif isinstance(error, MCPTimeoutError):
            log.error("mcp_timeout_error", error=str(error))
            error_info = get_error_info("3004")
            return {
                "status": "error",
                "error_code": "3004",
                "message": error_info["message"],
                "retry_allowed": True,
                "retry_after": error_info.get("retry_after"),
                "action": error_info.get("action"),
            }

        # Tool execution error
        elif isinstance(error, MCPToolError):
            log.error("mcp_tool_error", error=str(error), code=error.code)
            error_info = get_error_info(error.code or "3003")
            return {
                "status": "error",
                "error_code": error.code or "3003",
                "message": error.message or error_info["message"],
                "retry_allowed": error_info["retryable"],
                "action": error_info.get("action"),
                "details": error.details,
            }

        # Insufficient credits
        elif isinstance(error, InsufficientCreditsError):
            log.warning("insufficient_credits", error=str(error))
            error_info = get_error_info("6011")
            return {
                "status": "error",
                "error_code": "6011",
                "message": error_info["message"],
                "retry_allowed": False,
                "action": error_info.get("action"),
                "action_url": error_info.get("action_url"),
                "details": {
                    "required": error.required,
                    "available": error.available,
                },
            }

        # Unknown MCP error
        else:
            log.error("unknown_mcp_error", error=str(error), exc_info=True)
            error_info = get_error_info("3003")
            return {
                "status": "error",
                "error_code": "3003",
                "message": error_info["message"],
                "retry_allowed": True,
                "action": error_info.get("action"),
            }

    @staticmethod
    def handle_ai_model_error(error: Exception) -> dict[str, Any]:
        """
        Handle AI model (Gemini) errors.

        Args:
            error: The AI model exception that occurred

        Returns:
            Standardized error response dict
        """
        log = logger.bind(error_type=type(error).__name__)

        # Timeout error
        if isinstance(error, AIModelTimeoutError):
            log.error("ai_model_timeout", error=str(error))
            error_info = get_error_info("4002")
            return {
                "status": "error",
                "error_code": "4002",
                "message": error_info["message"],
                "retry_allowed": True,
                "retry_after": error_info.get("retry_after"),
                "action": error_info.get("action"),
            }

        # Quota exceeded
        elif isinstance(error, AIModelQuotaError):
            log.error("ai_model_quota_exceeded", error=str(error))
            error_info = get_error_info("4003")
            return {
                "status": "error",
                "error_code": "4003",
                "message": error_info["message"],
                "retry_allowed": True,
                "retry_after": error_info.get("retry_after"),
                "action": error_info.get("action"),
            }

        # Generic AI model error
        elif isinstance(error, (AIModelError, GeminiError)):
            log.error("ai_model_error", error=str(error))
            error_info = get_error_info("4001")
            return {
                "status": "error",
                "error_code": "4001",
                "message": error_info["message"],
                "retry_allowed": True,
                "retry_after": error_info.get("retry_after"),
                "action": error_info.get("action"),
            }

        # Unknown AI error
        else:
            log.error("unknown_ai_error", error=str(error), exc_info=True)
            error_info = get_error_info("4001")
            return {
                "status": "error",
                "error_code": "4001",
                "message": error_info["message"],
                "retry_allowed": True,
                "retry_after": error_info.get("retry_after"),
                "action": error_info.get("action"),
            }

    @staticmethod
    def handle_validation_error(error: Exception, field: str | None = None) -> dict[str, Any]:
        """
        Handle data validation errors.

        Args:
            error: The validation exception
            field: Optional field name that failed validation

        Returns:
            Standardized error response dict
        """
        log = logger.bind(error_type=type(error).__name__, field=field)
        log.warning("validation_error", error=str(error))

        error_info = get_error_info("1001")
        response = {
            "status": "error",
            "error_code": "1001",
            "message": error_info["message"],
            "retry_allowed": False,
        }

        if field:
            response["details"] = {
                "field": field,
                "error": str(error),
            }

        return response

    @staticmethod
    async def retry_with_backoff(
        func,
        max_retries: int = 3,
        backoff_factor: int = 2,
        retryable_errors: tuple = (
            PlatformServiceError,
            PlatformTimeoutError,
            MCPConnectionError,
            MCPTimeoutError,
            AIModelTimeoutError,
        ),
    ) -> Any:
        """
        Retry a function with exponential backoff.

        Args:
            func: Async function to retry
            max_retries: Maximum number of retry attempts
            backoff_factor: Multiplier for exponential backoff
            retryable_errors: Tuple of error types that should trigger retry

        Returns:
            Result from successful function call

        Raises:
            Last exception if all retries fail
        """
        last_error = None

        for attempt in range(max_retries):
            try:
                return await func()
            except retryable_errors as e:
                last_error = e
                if attempt < max_retries - 1:
                    wait_time = backoff_factor ** attempt
                    logger.warning(
                        "retry_attempt",
                        attempt=attempt + 1,
                        max_retries=max_retries,
                        wait_time=wait_time,
                        error=str(e),
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(
                        "retry_exhausted",
                        attempts=max_retries,
                        error=str(e),
                    )

        # All retries failed, raise last error
        if last_error:
            raise last_error

    @staticmethod
    def create_error_response(
        error: Exception,
        context: str,
        platform: str | None = None,
        retry_count: int = 0,
    ) -> dict[str, Any]:
        """
        Create a standardized error response for any exception.

        This is the main entry point for error handling in the Ad Performance module.
        It routes to the appropriate specialized handler based on error type.

        Args:
            error: The exception that occurred
            context: Context where error occurred (e.g., "fetch_ad_data")
            platform: Optional platform name for API errors
            retry_count: Current retry attempt number

        Returns:
            Standardized error response dict suitable for returning from execute()
        """
        log = logger.bind(
            context=context,
            platform=platform,
            retry_count=retry_count,
            error_type=type(error).__name__,
        )
        log.error("error_occurred", error=str(error))

        # Route to appropriate handler
        if isinstance(error, AdPlatformError):
            return AdPerformanceErrorHandler.handle_api_error(
                error=error,
                platform=platform or error.platform,
                retry_count=retry_count,
            )

        elif isinstance(error, (MCPConnectionError, MCPTimeoutError, MCPToolError, InsufficientCreditsError)):
            return AdPerformanceErrorHandler.handle_mcp_error(error)

        elif isinstance(error, (AIModelError, AIModelTimeoutError, AIModelQuotaError, GeminiError)):
            return AdPerformanceErrorHandler.handle_ai_model_error(error)

        elif isinstance(error, ValueError):
            return AdPerformanceErrorHandler.handle_validation_error(error)

        # Unknown error
        else:
            log.error("unknown_error", error=str(error), exc_info=True)
            error_info = get_error_info("1000")
            return {
                "status": "error",
                "error_code": "1000",
                "message": error_info["message"],
                "retry_allowed": False,
                "action": error_info.get("action"),
                "action_url": error_info.get("action_url"),
                "details": {
                    "context": context,
                    "error_type": type(error).__name__,
                },
            }
