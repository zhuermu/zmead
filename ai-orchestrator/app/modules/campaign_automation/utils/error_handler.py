"""
Error handling utilities for Campaign Automation module.

This module provides specialized error handling for ad platform APIs,
MCP calls, and AI model interactions specific to the Campaign Automation module.

Requirements: 4.4, 7.5, 9.1, 9.2, 9.3, 9.4, 9.5
"""

import asyncio
from datetime import datetime
from typing import Any

import structlog

from app.core.errors import (
    AIModelError,
    AIModelQuotaError,
    AIModelTimeoutError,
    get_error_info,
)
from app.services.gemini_client import GeminiError
from app.services.mcp_client import (
    InsufficientCreditsError,
    MCPConnectionError,
    MCPTimeoutError,
    MCPToolError,
)

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
        self.error_type = "AD_PLATFORM_ERROR"
        super().__init__(message)


class TokenExpiredError(AdPlatformError):
    """Raised when ad platform token has expired."""

    def __init__(self, platform: str, message: str = "Token expired"):
        super().__init__(
            message=message,
            platform=platform,
            code="6001",
        )
        self.error_type = "TOKEN_EXPIRED"


class TokenInvalidError(AdPlatformError):
    """Raised when ad platform token is invalid."""

    def __init__(self, platform: str, message: str = "Invalid token"):
        super().__init__(
            message=message,
            platform=platform,
            code="6001",
        )
        self.error_type = "TOKEN_INVALID"


class PermissionDeniedError(AdPlatformError):
    """Raised when access to ad platform resource is denied."""

    def __init__(self, platform: str, message: str = "Permission denied"):
        super().__init__(
            message=message,
            platform=platform,
            code="6001",
        )
        self.error_type = "PERMISSION_DENIED"


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
        self.error_type = "API_RATE_LIMIT"


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
        self.error_type = "PLATFORM_SERVICE_ERROR"


class PlatformTimeoutError(AdPlatformError):
    """Raised when ad platform API request times out."""

    def __init__(self, platform: str, message: str = "Request timeout"):
        super().__init__(
            message=message,
            platform=platform,
            code="4002",
        )
        self.error_type = "PLATFORM_TIMEOUT"


class BudgetInsufficientError(AdPlatformError):
    """Raised when ad account has insufficient budget."""

    def __init__(self, platform: str, message: str = "Insufficient budget"):
        super().__init__(
            message=message,
            platform=platform,
            code="6002",
        )
        self.error_type = "BUDGET_INSUFFICIENT"


class CreativeRejectedError(AdPlatformError):
    """Raised when creative is rejected by platform."""

    def __init__(self, platform: str, reason: str, message: str = "Creative rejected"):
        super().__init__(
            message=message,
            platform=platform,
            code="6003",
            details={"reason": reason},
        )
        self.error_type = "CREATIVE_REJECTED"


# Error Response Formatter


class ErrorResponseFormatter:
    """
    Format error responses for Campaign Automation module.

    Requirements: 9.3, 9.5
    """

    @staticmethod
    def format_error_response(
        error: Exception,
        context: str,
        platform: str | None = None,
        retry_count: int = 0,
    ) -> dict[str, Any]:
        """
        Format an error into a standardized response.

        Args:
            error: The exception that occurred
            context: Context where error occurred
            platform: Optional platform name
            retry_count: Current retry attempt number

        Returns:
            Standardized error response dict with:
            - status: "error"
            - error: dict with code, type, message, details
            - retry_allowed: Whether retry is allowed
            - retry_after: Seconds to wait before retry (if applicable)
            - timestamp: ISO format timestamp

        Requirements: 9.3, 9.5
        """
        timestamp = datetime.utcnow().isoformat()

        # Get error code and info
        if isinstance(error, AdPlatformError):
            code = error.code or "4002"
            error_type = error.error_type
            platform = platform or error.platform
        elif isinstance(error, MCPToolError):
            code = error.code or "3003"
            error_type = "MCP_TOOL_ERROR"
        elif isinstance(error, AIModelError):
            code = error.code
            error_type = "AI_MODEL_ERROR"
        else:
            code = "1000"
            error_type = "UNKNOWN_ERROR"

        error_info = get_error_info(code)

        response = {
            "status": "error",
            "error": {
                "code": code,
                "type": error_type,
                "message": error_info["message"],
                "context": context,
                "timestamp": timestamp,
            },
            "retry_allowed": error_info.get("retryable", False) and retry_count < 3,
        }

        # Add platform info if available
        if platform:
            response["error"]["platform"] = platform

        # Add retry_after if specified
        if "retry_after" in error_info:
            response["retry_after"] = error_info["retry_after"]

        # Add action info if available
        if error_info.get("action"):
            response["error"]["action"] = error_info["action"]
        if error_info.get("action_url"):
            response["error"]["action_url"] = error_info["action_url"]

        # Add error-specific details
        if isinstance(error, AdPlatformError) and error.details:
            response["error"]["details"] = error.details
        elif isinstance(error, MCPToolError) and error.details:
            response["error"]["details"] = error.details
        elif isinstance(error, AIModelError) and error.details:
            response["error"]["details"] = error.details
        elif isinstance(error, InsufficientCreditsError):
            response["error"]["details"] = {
                "required": error.required,
                "available": error.available,
            }

        return response


# Campaign Automation Error Handler


class CampaignAutomationErrorHandler:
    """
    Centralized error handling for Campaign Automation module.

    Handles errors from:
    - Ad platform APIs (Meta, TikTok, Google)
    - MCP client calls
    - AI model (Gemini) calls
    - Data validation

    Returns standardized error responses with retry information.

    Requirements: 4.4, 7.5, 9.1, 9.2, 9.3, 9.4, 9.5
    """

    @staticmethod
    def handle_api_error(
        error: Exception,
        platform: str,
        retry_count: int = 0,
        context: str = "api_call",
    ) -> dict[str, Any]:
        """
        Handle ad platform API errors.

        Args:
            error: The exception that occurred
            platform: Platform name (meta, tiktok, google)
            retry_count: Current retry attempt number
            context: Context where error occurred

        Returns:
            Standardized error response dict

        Requirements: 7.5, 9.1, 9.3, 9.5
        """
        log = logger.bind(
            platform=platform,
            retry_count=retry_count,
            context=context,
            error_type=type(error).__name__,
        )

        # Token expired or invalid (401/403)
        if isinstance(error, (TokenExpiredError, TokenInvalidError, PermissionDeniedError)):
            log.warning("token_error", error=str(error))
            return ErrorResponseFormatter.format_error_response(
                error=error,
                context=context,
                platform=platform,
                retry_count=retry_count,
            )

        # Rate limit exceeded (429)
        elif isinstance(error, RateLimitError):
            log.warning("rate_limit_error", retry_after=error.retry_after)
            response = ErrorResponseFormatter.format_error_response(
                error=error,
                context=context,
                platform=platform,
                retry_count=retry_count,
            )
            response["retry_after"] = error.retry_after
            return response

        # Platform service error (500)
        elif isinstance(error, PlatformServiceError):
            log.error("platform_service_error", status_code=error.details.get("status_code"))
            return ErrorResponseFormatter.format_error_response(
                error=error,
                context=context,
                platform=platform,
                retry_count=retry_count,
            )

        # Timeout error
        elif isinstance(error, PlatformTimeoutError):
            log.error("platform_timeout_error")
            return ErrorResponseFormatter.format_error_response(
                error=error,
                context=context,
                platform=platform,
                retry_count=retry_count,
            )

        # Budget insufficient
        elif isinstance(error, BudgetInsufficientError):
            log.warning("budget_insufficient", platform=platform)
            return ErrorResponseFormatter.format_error_response(
                error=error,
                context=context,
                platform=platform,
                retry_count=retry_count,
            )

        # Creative rejected
        elif isinstance(error, CreativeRejectedError):
            log.warning("creative_rejected", reason=error.details.get("reason"))
            return ErrorResponseFormatter.format_error_response(
                error=error,
                context=context,
                platform=platform,
                retry_count=retry_count,
            )

        # Generic ad platform error
        elif isinstance(error, AdPlatformError):
            log.error("ad_platform_error", error=str(error), code=error.code)
            return ErrorResponseFormatter.format_error_response(
                error=error,
                context=context,
                platform=platform,
                retry_count=retry_count,
            )

        # Unknown error
        else:
            log.error("unknown_api_error", error=str(error), exc_info=True)
            generic_error = AdPlatformError(
                message=str(error),
                platform=platform,
                code="4002",
            )
            return ErrorResponseFormatter.format_error_response(
                error=generic_error,
                context=context,
                platform=platform,
                retry_count=retry_count,
            )

    @staticmethod
    def handle_mcp_error(
        error: Exception,
        context: str = "mcp_call",
    ) -> dict[str, Any]:
        """
        Handle MCP client errors.

        Args:
            error: The MCP exception that occurred
            context: Context where error occurred

        Returns:
            Standardized error response dict

        Requirements: 9.3, 9.5
        """
        log = logger.bind(error_type=type(error).__name__, context=context)

        # Connection error
        if isinstance(error, MCPConnectionError):
            log.error("mcp_connection_error", error=str(error))
            return ErrorResponseFormatter.format_error_response(
                error=error,
                context=context,
            )

        # Timeout error
        elif isinstance(error, MCPTimeoutError):
            log.error("mcp_timeout_error", error=str(error))
            return ErrorResponseFormatter.format_error_response(
                error=error,
                context=context,
            )

        # Tool execution error
        elif isinstance(error, MCPToolError):
            log.error("mcp_tool_error", error=str(error), code=error.code)
            return ErrorResponseFormatter.format_error_response(
                error=error,
                context=context,
            )

        # Insufficient credits
        elif isinstance(error, InsufficientCreditsError):
            log.warning("insufficient_credits", error=str(error))
            return ErrorResponseFormatter.format_error_response(
                error=error,
                context=context,
            )

        # Unknown MCP error
        else:
            log.error("unknown_mcp_error", error=str(error), exc_info=True)
            generic_error = MCPToolError(
                message=str(error),
                code="3003",
            )
            return ErrorResponseFormatter.format_error_response(
                error=generic_error,
                context=context,
            )

    @staticmethod
    def handle_ai_model_error(
        error: Exception,
        context: str = "ai_generation",
    ) -> dict[str, Any]:
        """
        Handle AI model (Gemini) errors.

        Args:
            error: The AI model exception that occurred
            context: Context where error occurred

        Returns:
            Standardized error response dict

        Requirements: 9.3, 9.5
        """
        log = logger.bind(error_type=type(error).__name__, context=context)

        # Timeout error
        if isinstance(error, AIModelTimeoutError):
            log.error("ai_model_timeout", error=str(error))
            return ErrorResponseFormatter.format_error_response(
                error=error,
                context=context,
            )

        # Quota exceeded
        elif isinstance(error, AIModelQuotaError):
            log.error("ai_model_quota_exceeded", error=str(error))
            return ErrorResponseFormatter.format_error_response(
                error=error,
                context=context,
            )

        # Generic AI model error
        elif isinstance(error, (AIModelError, GeminiError)):
            log.error("ai_model_error", error=str(error))
            return ErrorResponseFormatter.format_error_response(
                error=error,
                context=context,
            )

        # Unknown AI error
        else:
            log.error("unknown_ai_error", error=str(error), exc_info=True)
            generic_error = AIModelError(
                message=str(error),
                code="4001",
            )
            return ErrorResponseFormatter.format_error_response(
                error=generic_error,
                context=context,
            )

    @staticmethod
    def handle_validation_error(
        error: Exception,
        field: str | None = None,
        context: str = "validation",
    ) -> dict[str, Any]:
        """
        Handle data validation errors.

        Args:
            error: The validation exception
            field: Optional field name that failed validation
            context: Context where error occurred

        Returns:
            Standardized error response dict

        Requirements: 9.3, 9.5
        """
        log = logger.bind(error_type=type(error).__name__, field=field, context=context)
        log.warning("validation_error", error=str(error))

        error_info = get_error_info("1001")
        response = {
            "status": "error",
            "error": {
                "code": "1001",
                "type": "VALIDATION_ERROR",
                "message": error_info["message"],
                "context": context,
                "timestamp": datetime.utcnow().isoformat(),
            },
            "retry_allowed": False,
        }

        if field:
            response["error"]["details"] = {
                "field": field,
                "error": str(error),
            }

        return response

    @staticmethod
    async def retry_with_backoff(
        func,
        max_retries: int = 3,
        backoff_factor: int = 2,
        timeout: int = 30,
        retryable_errors: tuple = (
            PlatformServiceError,
            PlatformTimeoutError,
            MCPConnectionError,
            MCPTimeoutError,
            AIModelTimeoutError,
            asyncio.TimeoutError,
        ),
        context: str = "operation",
    ) -> Any:
        """
        Retry a function with exponential backoff.

        Args:
            func: Async function to retry
            max_retries: Maximum number of retry attempts (default 3)
            backoff_factor: Multiplier for exponential backoff (default 2)
            timeout: Timeout in seconds for each attempt (default 30)
            retryable_errors: Tuple of error types that should trigger retry
            context: Context string for logging

        Returns:
            Result from successful function call

        Raises:
            Last exception if all retries fail

        Requirements: 4.4, 9.1, 9.2, 9.4
        """
        last_error = None

        for attempt in range(max_retries):
            try:
                # Execute with timeout
                return await asyncio.wait_for(func(), timeout=timeout)

            except asyncio.TimeoutError as e:
                last_error = e
                if attempt < max_retries - 1:
                    wait_time = backoff_factor**attempt
                    logger.warning(
                        "retry_timeout",
                        context=context,
                        attempt=attempt + 1,
                        max_retries=max_retries,
                        wait_time=wait_time,
                        timeout=timeout,
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(
                        "retry_exhausted_timeout",
                        context=context,
                        attempts=max_retries,
                        timeout=timeout,
                    )

            except retryable_errors as e:
                last_error = e
                if attempt < max_retries - 1:
                    wait_time = backoff_factor**attempt
                    logger.warning(
                        "retry_attempt",
                        context=context,
                        attempt=attempt + 1,
                        max_retries=max_retries,
                        wait_time=wait_time,
                        error=str(e),
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(
                        "retry_exhausted",
                        context=context,
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

        This is the main entry point for error handling in the Campaign Automation module.
        It routes to the appropriate specialized handler based on error type.

        Args:
            error: The exception that occurred
            context: Context where error occurred
            platform: Optional platform name for API errors
            retry_count: Current retry attempt number

        Returns:
            Standardized error response dict suitable for returning from execute()

        Requirements: 9.3, 9.5
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
            return CampaignAutomationErrorHandler.handle_api_error(
                error=error,
                platform=platform or error.platform,
                retry_count=retry_count,
                context=context,
            )

        elif isinstance(
            error,
            (MCPConnectionError, MCPTimeoutError, MCPToolError, InsufficientCreditsError),
        ):
            return CampaignAutomationErrorHandler.handle_mcp_error(
                error=error,
                context=context,
            )

        elif isinstance(error, (AIModelError, AIModelTimeoutError, AIModelQuotaError, GeminiError)):
            return CampaignAutomationErrorHandler.handle_ai_model_error(
                error=error,
                context=context,
            )

        elif isinstance(error, ValueError):
            return CampaignAutomationErrorHandler.handle_validation_error(
                error=error,
                context=context,
            )

        # Unknown error
        else:
            log.error("unknown_error", error=str(error), exc_info=True)
            error_info = get_error_info("1000")
            return {
                "status": "error",
                "error": {
                    "code": "1000",
                    "type": "UNKNOWN_ERROR",
                    "message": error_info["message"],
                    "context": context,
                    "timestamp": datetime.utcnow().isoformat(),
                },
                "retry_allowed": False,
                "action": error_info.get("action"),
                "action_url": error_info.get("action_url"),
                "details": {
                    "error_type": type(error).__name__,
                },
            }
