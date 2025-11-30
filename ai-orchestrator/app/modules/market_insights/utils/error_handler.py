"""
Error handling utilities for Market Insights module.

This module provides specialized error handling for third-party APIs
(TikTok Creative Center, pytrends), AI model interactions, and MCP calls
specific to the Market Insights module.

Requirements: 1.5, 5.5, 6.3, 6.4, 6.5, 6.6
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
from app.modules.market_insights.utils.retry_strategy import (
    APIError,
    RateLimitError as RetryRateLimitError,
    RetryableError,
    TimeoutError as RetryTimeoutError,
)
from app.services.gemini_client import GeminiError
from app.services.mcp_client import (
    InsufficientCreditsError,
    MCPConnectionError,
    MCPTimeoutError,
    MCPToolError,
)

logger = structlog.get_logger(__name__)


# Third-Party API Errors


class ThirdPartyAPIError(Exception):
    """Base class for third-party API errors."""

    def __init__(
        self,
        message: str,
        api_source: str,
        code: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        self.message = message
        self.api_source = api_source
        self.code = code
        self.details = details or {}
        self.error_type = "THIRD_PARTY_API_ERROR"
        super().__init__(message)


class TikTokAPIError(ThirdPartyAPIError):
    """Raised when TikTok Creative Center API fails."""

    def __init__(
        self,
        message: str = "TikTok API error",
        code: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=message,
            api_source="tiktok_creative_center",
            code=code or "4002",
            details=details,
        )
        self.error_type = "TIKTOK_API_ERROR"


class TikTokRateLimitError(TikTokAPIError):
    """Raised when TikTok API rate limit is exceeded."""

    def __init__(
        self,
        retry_after: int = 60,
        message: str = "TikTok API rate limit exceeded",
    ):
        super().__init__(
            message=message,
            code="1003",
            details={"retry_after": retry_after},
        )
        self.retry_after = retry_after
        self.error_type = "TIKTOK_RATE_LIMIT"


class TikTokAuthError(TikTokAPIError):
    """Raised when TikTok API authentication fails."""

    def __init__(self, message: str = "TikTok API authentication failed"):
        super().__init__(
            message=message,
            code="6001",
        )
        self.error_type = "TIKTOK_AUTH_ERROR"


class TikTokServiceError(TikTokAPIError):
    """Raised when TikTok API service returns 5xx error."""

    def __init__(
        self,
        status_code: int,
        message: str = "TikTok API service error",
    ):
        super().__init__(
            message=message,
            code="4002",
            details={"status_code": status_code},
        )
        self.error_type = "TIKTOK_SERVICE_ERROR"


class PyTrendsError(ThirdPartyAPIError):
    """Raised when pytrends (Google Trends) fails."""

    def __init__(
        self,
        message: str = "Google Trends API error",
        code: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=message,
            api_source="pytrends",
            code=code or "4002",
            details=details,
        )
        self.error_type = "PYTRENDS_ERROR"


class PyTrendsRateLimitError(PyTrendsError):
    """Raised when pytrends rate limit is exceeded."""

    def __init__(
        self,
        retry_after: int = 60,
        message: str = "Google Trends rate limit exceeded",
    ):
        super().__init__(
            message=message,
            code="1003",
            details={"retry_after": retry_after},
        )
        self.retry_after = retry_after
        self.error_type = "PYTRENDS_RATE_LIMIT"


class PyTrendsTimeoutError(PyTrendsError):
    """Raised when pytrends request times out."""

    def __init__(self, message: str = "Google Trends request timeout"):
        super().__init__(
            message=message,
            code="4002",
        )
        self.error_type = "PYTRENDS_TIMEOUT"


# Competitor Analysis Errors


class CompetitorAnalysisError(Exception):
    """Base class for competitor analysis errors."""

    def __init__(
        self,
        message: str,
        code: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        self.message = message
        self.code = code or "4001"
        self.details = details or {}
        self.error_type = "COMPETITOR_ANALYSIS_ERROR"
        super().__init__(message)


class InvalidURLError(CompetitorAnalysisError):
    """Raised when competitor URL is invalid."""

    def __init__(self, url: str, message: str = "Invalid competitor URL"):
        super().__init__(
            message=message,
            code="1001",
            details={"url": url},
        )
        self.error_type = "INVALID_URL"


class URLAccessError(CompetitorAnalysisError):
    """Raised when competitor URL cannot be accessed."""

    def __init__(self, url: str, message: str = "Cannot access competitor URL"):
        super().__init__(
            message=message,
            code="4002",
            details={"url": url},
        )
        self.error_type = "URL_ACCESS_ERROR"


# Strategy Tracking Errors


class StrategyTrackingError(Exception):
    """Base class for strategy tracking errors."""

    def __init__(
        self,
        message: str,
        code: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        self.message = message
        self.code = code or "5000"
        self.details = details or {}
        self.error_type = "STRATEGY_TRACKING_ERROR"
        super().__init__(message)


class StrategyNotFoundError(StrategyTrackingError):
    """Raised when strategy is not found."""

    def __init__(self, strategy_id: str, message: str = "Strategy not found"):
        super().__init__(
            message=message,
            code="5000",
            details={"strategy_id": strategy_id},
        )
        self.error_type = "STRATEGY_NOT_FOUND"


class CampaignDataError(StrategyTrackingError):
    """Raised when campaign data cannot be retrieved."""

    def __init__(
        self,
        campaign_ids: list[str],
        message: str = "Failed to retrieve campaign data",
    ):
        super().__init__(
            message=message,
            code="5000",
            details={"campaign_ids": campaign_ids},
        )
        self.error_type = "CAMPAIGN_DATA_ERROR"


# Error Response Formatter


class ErrorResponseFormatter:
    """
    Format error responses for Market Insights module.

    Requirements: 1.5, 5.5, 6.6
    """

    @staticmethod
    def format_error_response(
        error: Exception,
        context: str,
        api_source: str | None = None,
        retry_count: int = 0,
    ) -> dict[str, Any]:
        """
        Format an error into a standardized response.

        Args:
            error: The exception that occurred
            context: Context where error occurred
            api_source: Optional API source name
            retry_count: Current retry attempt number

        Returns:
            Standardized error response dict with:
            - status: "error"
            - error: dict with code, type, message, details
            - retry_allowed: Whether retry is allowed
            - retry_after: Seconds to wait before retry (if applicable)
            - timestamp: ISO format timestamp

        Requirements: 1.5, 5.5, 6.6
        """
        timestamp = datetime.utcnow().isoformat()

        # Get error code and info
        if isinstance(error, ThirdPartyAPIError):
            code = error.code or "4002"
            error_type = error.error_type
            api_source = api_source or error.api_source
        elif isinstance(error, CompetitorAnalysisError):
            code = error.code or "4001"
            error_type = error.error_type
        elif isinstance(error, StrategyTrackingError):
            code = error.code or "5000"
            error_type = error.error_type
        elif isinstance(error, MCPToolError):
            code = error.code or "3003"
            error_type = "MCP_TOOL_ERROR"
        elif isinstance(error, AIModelError):
            code = error.code
            error_type = "AI_MODEL_ERROR"
        elif isinstance(error, (RetryableError, RetryRateLimitError, RetryTimeoutError)):
            code = "4002"
            error_type = getattr(error, "error_type", "RETRYABLE_ERROR")
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

        # Add API source info if available
        if api_source:
            response["error"]["api_source"] = api_source

        # Add retry_after if specified
        if "retry_after" in error_info:
            response["retry_after"] = error_info["retry_after"]

        # Add action info if available
        if error_info.get("action"):
            response["error"]["action"] = error_info["action"]
        if error_info.get("action_url"):
            response["error"]["action_url"] = error_info["action_url"]

        # Add error-specific details
        if isinstance(error, ThirdPartyAPIError) and error.details:
            response["error"]["details"] = error.details
        elif isinstance(error, CompetitorAnalysisError) and error.details:
            response["error"]["details"] = error.details
        elif isinstance(error, StrategyTrackingError) and error.details:
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


# Market Insights Error Handler


class MarketInsightsErrorHandler:
    """
    Centralized error handling for Market Insights module.

    Handles errors from:
    - Third-party APIs (TikTok Creative Center, pytrends)
    - MCP client calls
    - AI model (Gemini) calls
    - Data validation
    - Competitor analysis
    - Strategy tracking

    Returns standardized error responses with retry information.

    Requirements: 1.5, 5.5, 6.3, 6.4, 6.5, 6.6
    """

    @staticmethod
    def handle_api_error(
        error: Exception,
        api_source: str,
        retry_count: int = 0,
        context: str = "api_call",
    ) -> dict[str, Any]:
        """
        Handle third-party API errors (TikTok, pytrends).

        Args:
            error: The exception that occurred
            api_source: API source name (tiktok, pytrends)
            retry_count: Current retry attempt number
            context: Context where error occurred

        Returns:
            Standardized error response dict

        Requirements: 6.3, 6.4, 6.5, 6.6
        """
        log = logger.bind(
            api_source=api_source,
            retry_count=retry_count,
            context=context,
            error_type=type(error).__name__,
        )

        # TikTok API errors
        if isinstance(error, TikTokAuthError):
            log.warning("tiktok_auth_error", error=str(error))
            return ErrorResponseFormatter.format_error_response(
                error=error,
                context=context,
                api_source=api_source,
                retry_count=retry_count,
            )

        elif isinstance(error, TikTokRateLimitError):
            log.warning("tiktok_rate_limit", retry_after=error.retry_after)
            response = ErrorResponseFormatter.format_error_response(
                error=error,
                context=context,
                api_source=api_source,
                retry_count=retry_count,
            )
            response["retry_after"] = error.retry_after
            return response

        elif isinstance(error, TikTokServiceError):
            log.error("tiktok_service_error", status_code=error.details.get("status_code"))
            return ErrorResponseFormatter.format_error_response(
                error=error,
                context=context,
                api_source=api_source,
                retry_count=retry_count,
            )

        elif isinstance(error, TikTokAPIError):
            log.error("tiktok_api_error", error=str(error))
            return ErrorResponseFormatter.format_error_response(
                error=error,
                context=context,
                api_source=api_source,
                retry_count=retry_count,
            )

        # pytrends errors
        elif isinstance(error, PyTrendsRateLimitError):
            log.warning("pytrends_rate_limit", retry_after=error.retry_after)
            response = ErrorResponseFormatter.format_error_response(
                error=error,
                context=context,
                api_source=api_source,
                retry_count=retry_count,
            )
            response["retry_after"] = error.retry_after
            return response

        elif isinstance(error, PyTrendsTimeoutError):
            log.error("pytrends_timeout")
            return ErrorResponseFormatter.format_error_response(
                error=error,
                context=context,
                api_source=api_source,
                retry_count=retry_count,
            )

        elif isinstance(error, PyTrendsError):
            log.error("pytrends_error", error=str(error))
            return ErrorResponseFormatter.format_error_response(
                error=error,
                context=context,
                api_source=api_source,
                retry_count=retry_count,
            )

        # Generic third-party API error
        elif isinstance(error, ThirdPartyAPIError):
            log.error("third_party_api_error", error=str(error), code=error.code)
            return ErrorResponseFormatter.format_error_response(
                error=error,
                context=context,
                api_source=api_source,
                retry_count=retry_count,
            )

        # Retry strategy errors
        elif isinstance(error, RetryRateLimitError):
            log.warning("rate_limit_error", retry_after=getattr(error, "retry_after", 60))
            response = ErrorResponseFormatter.format_error_response(
                error=error,
                context=context,
                api_source=api_source,
                retry_count=retry_count,
            )
            response["retry_after"] = getattr(error, "retry_after", 60)
            return response

        elif isinstance(error, (RetryTimeoutError, asyncio.TimeoutError)):
            log.error("timeout_error")
            return ErrorResponseFormatter.format_error_response(
                error=error,
                context=context,
                api_source=api_source,
                retry_count=retry_count,
            )

        elif isinstance(error, (RetryableError, APIError)):
            log.error("retryable_error", error=str(error))
            return ErrorResponseFormatter.format_error_response(
                error=error,
                context=context,
                api_source=api_source,
                retry_count=retry_count,
            )

        # Unknown error
        else:
            log.error("unknown_api_error", error=str(error), exc_info=True)
            generic_error = ThirdPartyAPIError(
                message=str(error),
                api_source=api_source,
                code="4002",
            )
            return ErrorResponseFormatter.format_error_response(
                error=generic_error,
                context=context,
                api_source=api_source,
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

        Requirements: 6.6
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
        context: str = "ai_analysis",
    ) -> dict[str, Any]:
        """
        Handle AI model (Gemini) errors.

        Args:
            error: The AI model exception that occurred
            context: Context where error occurred

        Returns:
            Standardized error response dict

        Requirements: 1.5, 6.6
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

        Requirements: 1.5
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
    def handle_competitor_analysis_error(
        error: Exception,
        context: str = "competitor_analysis",
    ) -> dict[str, Any]:
        """
        Handle competitor analysis errors.

        Args:
            error: The exception that occurred
            context: Context where error occurred

        Returns:
            Standardized error response dict

        Requirements: 1.5
        """
        log = logger.bind(error_type=type(error).__name__, context=context)

        if isinstance(error, InvalidURLError):
            log.warning("invalid_url", url=error.details.get("url"))
            return ErrorResponseFormatter.format_error_response(
                error=error,
                context=context,
            )

        elif isinstance(error, URLAccessError):
            log.error("url_access_error", url=error.details.get("url"))
            return ErrorResponseFormatter.format_error_response(
                error=error,
                context=context,
            )

        elif isinstance(error, CompetitorAnalysisError):
            log.error("competitor_analysis_error", error=str(error))
            return ErrorResponseFormatter.format_error_response(
                error=error,
                context=context,
            )

        else:
            log.error("unknown_competitor_error", error=str(error), exc_info=True)
            generic_error = CompetitorAnalysisError(
                message=str(error),
                code="4001",
            )
            return ErrorResponseFormatter.format_error_response(
                error=generic_error,
                context=context,
            )

    @staticmethod
    def handle_strategy_tracking_error(
        error: Exception,
        context: str = "strategy_tracking",
    ) -> dict[str, Any]:
        """
        Handle strategy tracking errors.

        Args:
            error: The exception that occurred
            context: Context where error occurred

        Returns:
            Standardized error response dict

        Requirements: 5.5
        """
        log = logger.bind(error_type=type(error).__name__, context=context)

        if isinstance(error, StrategyNotFoundError):
            log.warning("strategy_not_found", strategy_id=error.details.get("strategy_id"))
            return ErrorResponseFormatter.format_error_response(
                error=error,
                context=context,
            )

        elif isinstance(error, CampaignDataError):
            log.error("campaign_data_error", campaign_ids=error.details.get("campaign_ids"))
            return ErrorResponseFormatter.format_error_response(
                error=error,
                context=context,
            )

        elif isinstance(error, StrategyTrackingError):
            log.error("strategy_tracking_error", error=str(error))
            return ErrorResponseFormatter.format_error_response(
                error=error,
                context=context,
            )

        else:
            log.error("unknown_tracking_error", error=str(error), exc_info=True)
            generic_error = StrategyTrackingError(
                message=str(error),
                code="5000",
            )
            return ErrorResponseFormatter.format_error_response(
                error=generic_error,
                context=context,
            )

    @staticmethod
    async def retry_with_backoff(
        func,
        max_retries: int = 3,
        backoff_factor: int = 2,
        timeout: int = 30,
        retryable_errors: tuple = (
            TikTokServiceError,
            PyTrendsTimeoutError,
            MCPConnectionError,
            MCPTimeoutError,
            AIModelTimeoutError,
            asyncio.TimeoutError,
            RetryableError,
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

        Requirements: 6.3, 6.5
        """
        last_error = None

        for attempt in range(max_retries):
            try:
                # Execute with timeout
                return await asyncio.wait_for(func(), timeout=timeout)

            except asyncio.TimeoutError as e:
                last_error = e
                if attempt < max_retries - 1:
                    wait_time = backoff_factor ** attempt
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
                    wait_time = backoff_factor ** attempt
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
        api_source: str | None = None,
        retry_count: int = 0,
    ) -> dict[str, Any]:
        """
        Create a standardized error response for any exception.

        This is the main entry point for error handling in the Market Insights module.
        It routes to the appropriate specialized handler based on error type.

        Args:
            error: The exception that occurred
            context: Context where error occurred
            api_source: Optional API source name for third-party API errors
            retry_count: Current retry attempt number

        Returns:
            Standardized error response dict suitable for returning from execute()

        Requirements: 1.5, 5.5, 6.6
        """
        log = logger.bind(
            context=context,
            api_source=api_source,
            retry_count=retry_count,
            error_type=type(error).__name__,
        )
        log.error("error_occurred", error=str(error))

        # Route to appropriate handler
        if isinstance(error, ThirdPartyAPIError):
            return MarketInsightsErrorHandler.handle_api_error(
                error=error,
                api_source=api_source or error.api_source,
                retry_count=retry_count,
                context=context,
            )

        elif isinstance(error, (RetryableError, RetryRateLimitError, RetryTimeoutError, APIError)):
            return MarketInsightsErrorHandler.handle_api_error(
                error=error,
                api_source=api_source or "unknown",
                retry_count=retry_count,
                context=context,
            )

        elif isinstance(error, CompetitorAnalysisError):
            return MarketInsightsErrorHandler.handle_competitor_analysis_error(
                error=error,
                context=context,
            )

        elif isinstance(error, StrategyTrackingError):
            return MarketInsightsErrorHandler.handle_strategy_tracking_error(
                error=error,
                context=context,
            )

        elif isinstance(
            error,
            (MCPConnectionError, MCPTimeoutError, MCPToolError, InsufficientCreditsError),
        ):
            return MarketInsightsErrorHandler.handle_mcp_error(
                error=error,
                context=context,
            )

        elif isinstance(error, (AIModelError, AIModelTimeoutError, AIModelQuotaError, GeminiError)):
            return MarketInsightsErrorHandler.handle_ai_model_error(
                error=error,
                context=context,
            )

        elif isinstance(error, ValueError):
            return MarketInsightsErrorHandler.handle_validation_error(
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
