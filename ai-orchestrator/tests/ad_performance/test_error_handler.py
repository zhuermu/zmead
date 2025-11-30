"""
Tests for Ad Performance error handling.

This module tests the error handling utilities for the Ad Performance module,
including API errors, MCP errors, and AI model errors.

Requirements: 8.5
"""

import pytest
from unittest.mock import AsyncMock, Mock

from app.modules.ad_performance.utils.error_handler import (
    AdPerformanceErrorHandler,
    AdPlatformError,
    TokenExpiredError,
    TokenInvalidError,
    PermissionDeniedError,
    RateLimitError,
    PlatformServiceError,
    PlatformTimeoutError,
)
from app.services.mcp_client import (
    MCPConnectionError,
    MCPTimeoutError,
    MCPToolError,
    InsufficientCreditsError,
)
from app.core.errors import (
    AIModelError,
    AIModelTimeoutError,
    AIModelQuotaError,
)


class TestHandleAPIError:
    """Test handling of ad platform API errors."""

    def test_token_expired_error(self):
        """Test handling of token expired error (401)."""
        error = TokenExpiredError(platform="meta")
        result = AdPerformanceErrorHandler.handle_api_error(
            error=error,
            platform="meta",
            retry_count=0,
        )

        assert result["status"] == "error"
        assert result["error_code"] == "6001"
        assert result["retry_allowed"] is False
        assert result["platform"] == "meta"
        assert "action" in result
        assert "action_url" in result

    def test_token_invalid_error(self):
        """Test handling of invalid token error (403)."""
        error = TokenInvalidError(platform="tiktok")
        result = AdPerformanceErrorHandler.handle_api_error(
            error=error,
            platform="tiktok",
            retry_count=0,
        )

        assert result["status"] == "error"
        assert result["error_code"] == "6001"
        assert result["retry_allowed"] is False
        assert result["platform"] == "tiktok"

    def test_permission_denied_error(self):
        """Test handling of permission denied error (403)."""
        error = PermissionDeniedError(platform="google")
        result = AdPerformanceErrorHandler.handle_api_error(
            error=error,
            platform="google",
            retry_count=0,
        )

        assert result["status"] == "error"
        assert result["error_code"] == "6001"
        assert result["retry_allowed"] is False

    def test_rate_limit_error(self):
        """Test handling of rate limit error (429)."""
        error = RateLimitError(platform="meta", retry_after=120)
        result = AdPerformanceErrorHandler.handle_api_error(
            error=error,
            platform="meta",
            retry_count=0,
        )

        assert result["status"] == "error"
        assert result["error_code"] == "1003"
        assert result["retry_allowed"] is True
        assert result["retry_after"] == 120
        assert result["platform"] == "meta"

    def test_platform_service_error_with_retries(self):
        """Test handling of platform service error (500) with retries available."""
        error = PlatformServiceError(platform="tiktok", status_code=500)
        result = AdPerformanceErrorHandler.handle_api_error(
            error=error,
            platform="tiktok",
            retry_count=0,
        )

        assert result["status"] == "error"
        assert result["error_code"] == "4002"
        assert result["retry_allowed"] is True
        assert result["retry_after"] == 1  # 2^0

    def test_platform_service_error_exhausted_retries(self):
        """Test handling of platform service error after max retries."""
        error = PlatformServiceError(platform="meta", status_code=503)
        result = AdPerformanceErrorHandler.handle_api_error(
            error=error,
            platform="meta",
            retry_count=3,
        )

        assert result["status"] == "error"
        assert result["error_code"] == "4002"
        assert result["retry_allowed"] is False

    def test_platform_timeout_error_with_retries(self):
        """Test handling of timeout error with retries available."""
        error = PlatformTimeoutError(platform="google")
        result = AdPerformanceErrorHandler.handle_api_error(
            error=error,
            platform="google",
            retry_count=1,
        )

        assert result["status"] == "error"
        assert result["error_code"] == "4002"
        assert result["retry_allowed"] is True
        assert result["retry_after"] == 2  # 2^1

    def test_platform_timeout_error_exhausted_retries(self):
        """Test handling of timeout error after max retries."""
        error = PlatformTimeoutError(platform="meta")
        result = AdPerformanceErrorHandler.handle_api_error(
            error=error,
            platform="meta",
            retry_count=3,
        )

        assert result["status"] == "error"
        assert result["error_code"] == "4002"
        assert result["retry_allowed"] is False

    def test_generic_ad_platform_error(self):
        """Test handling of generic ad platform error."""
        error = AdPlatformError(
            message="Unknown API error",
            platform="tiktok",
            code="4002",
        )
        result = AdPerformanceErrorHandler.handle_api_error(
            error=error,
            platform="tiktok",
            retry_count=0,
        )

        assert result["status"] == "error"
        assert result["error_code"] == "4002"
        assert result["retry_allowed"] is True

    def test_unknown_error_with_retries(self):
        """Test handling of unknown error with retries available."""
        error = Exception("Unknown error")
        result = AdPerformanceErrorHandler.handle_api_error(
            error=error,
            platform="meta",
            retry_count=0,
        )

        assert result["status"] == "error"
        assert result["error_code"] == "4002"
        assert result["retry_allowed"] is True

    def test_unknown_error_exhausted_retries(self):
        """Test handling of unknown error after max retries."""
        error = Exception("Unknown error")
        result = AdPerformanceErrorHandler.handle_api_error(
            error=error,
            platform="meta",
            retry_count=3,
        )

        assert result["status"] == "error"
        assert result["error_code"] == "4002"
        assert result["retry_allowed"] is False


class TestHandleMCPError:
    """Test handling of MCP client errors."""

    def test_mcp_connection_error(self):
        """Test handling of MCP connection error."""
        error = MCPConnectionError("Connection failed")
        result = AdPerformanceErrorHandler.handle_mcp_error(error)

        assert result["status"] == "error"
        assert result["error_code"] == "3000"
        assert result["retry_allowed"] is True
        assert "retry_after" in result
        assert "action" in result

    def test_mcp_timeout_error(self):
        """Test handling of MCP timeout error."""
        error = MCPTimeoutError("Request timed out")
        result = AdPerformanceErrorHandler.handle_mcp_error(error)

        assert result["status"] == "error"
        assert result["error_code"] == "3004"
        assert result["retry_allowed"] is True
        assert "retry_after" in result

    def test_mcp_tool_error(self):
        """Test handling of MCP tool execution error."""
        error = MCPToolError(
            message="Tool execution failed",
            code="3003",
            details={"tool": "save_metrics"},
        )
        result = AdPerformanceErrorHandler.handle_mcp_error(error)

        assert result["status"] == "error"
        assert result["error_code"] == "3003"
        assert result["retry_allowed"] is True
        assert result["details"]["tool"] == "save_metrics"

    def test_insufficient_credits_error(self):
        """Test handling of insufficient credits error."""
        error = InsufficientCreditsError(required=100, available=50)
        result = AdPerformanceErrorHandler.handle_mcp_error(error)

        assert result["status"] == "error"
        assert result["error_code"] == "6011"
        assert result["retry_allowed"] is False
        assert result["details"]["required"] == 100
        assert result["details"]["available"] == 50
        assert "action" in result
        assert "action_url" in result

    def test_unknown_mcp_error(self):
        """Test handling of unknown MCP error."""
        error = Exception("Unknown MCP error")
        result = AdPerformanceErrorHandler.handle_mcp_error(error)

        assert result["status"] == "error"
        assert result["error_code"] == "3003"
        assert result["retry_allowed"] is True


class TestHandleAIModelError:
    """Test handling of AI model errors."""

    def test_ai_model_timeout_error(self):
        """Test handling of AI model timeout error."""
        error = AIModelTimeoutError()
        result = AdPerformanceErrorHandler.handle_ai_model_error(error)

        assert result["status"] == "error"
        assert result["error_code"] == "4002"
        assert result["retry_allowed"] is True
        assert "retry_after" in result

    def test_ai_model_quota_error(self):
        """Test handling of AI model quota exceeded error."""
        error = AIModelQuotaError()
        result = AdPerformanceErrorHandler.handle_ai_model_error(error)

        assert result["status"] == "error"
        assert result["error_code"] == "4003"
        assert result["retry_allowed"] is True
        assert "retry_after" in result

    def test_ai_model_error(self):
        """Test handling of generic AI model error."""
        error = AIModelError(message="Model error")
        result = AdPerformanceErrorHandler.handle_ai_model_error(error)

        assert result["status"] == "error"
        assert result["error_code"] == "4001"
        assert result["retry_allowed"] is True

    def test_unknown_ai_error(self):
        """Test handling of unknown AI error."""
        error = Exception("Unknown AI error")
        result = AdPerformanceErrorHandler.handle_ai_model_error(error)

        assert result["status"] == "error"
        assert result["error_code"] == "4001"
        assert result["retry_allowed"] is True


class TestHandleValidationError:
    """Test handling of validation errors."""

    def test_validation_error_with_field(self):
        """Test handling of validation error with field name."""
        error = ValueError("Invalid date format")
        result = AdPerformanceErrorHandler.handle_validation_error(
            error=error,
            field="date",
        )

        assert result["status"] == "error"
        assert result["error_code"] == "1001"
        assert result["retry_allowed"] is False
        assert result["details"]["field"] == "date"
        assert "Invalid date format" in result["details"]["error"]

    def test_validation_error_without_field(self):
        """Test handling of validation error without field name."""
        error = ValueError("Invalid data")
        result = AdPerformanceErrorHandler.handle_validation_error(error)

        assert result["status"] == "error"
        assert result["error_code"] == "1001"
        assert result["retry_allowed"] is False


class TestRetryWithBackoff:
    """Test retry mechanism with exponential backoff."""

    @pytest.mark.asyncio
    async def test_successful_first_attempt(self):
        """Test successful execution on first attempt."""
        mock_func = AsyncMock(return_value="success")
        result = await AdPerformanceErrorHandler.retry_with_backoff(mock_func)

        assert result == "success"
        assert mock_func.call_count == 1

    @pytest.mark.asyncio
    async def test_successful_after_retries(self):
        """Test successful execution after retries."""
        mock_func = AsyncMock(
            side_effect=[
                PlatformTimeoutError(platform="meta"),
                PlatformTimeoutError(platform="meta"),
                "success",
            ]
        )
        result = await AdPerformanceErrorHandler.retry_with_backoff(
            mock_func,
            max_retries=3,
        )

        assert result == "success"
        assert mock_func.call_count == 3

    @pytest.mark.asyncio
    async def test_exhausted_retries(self):
        """Test failure after exhausting all retries."""
        mock_func = AsyncMock(
            side_effect=PlatformTimeoutError(platform="meta")
        )

        with pytest.raises(PlatformTimeoutError):
            await AdPerformanceErrorHandler.retry_with_backoff(
                mock_func,
                max_retries=3,
            )

        assert mock_func.call_count == 3

    @pytest.mark.asyncio
    async def test_non_retryable_error(self):
        """Test that non-retryable errors are raised immediately."""
        mock_func = AsyncMock(side_effect=TokenExpiredError(platform="meta"))

        with pytest.raises(TokenExpiredError):
            await AdPerformanceErrorHandler.retry_with_backoff(mock_func)

        assert mock_func.call_count == 1


class TestCreateErrorResponse:
    """Test unified error response creation."""

    def test_ad_platform_error_routing(self):
        """Test routing of ad platform errors."""
        error = TokenExpiredError(platform="meta")
        result = AdPerformanceErrorHandler.create_error_response(
            error=error,
            context="fetch_ad_data",
            platform="meta",
        )

        assert result["status"] == "error"
        assert result["error_code"] == "6001"
        assert result["platform"] == "meta"

    def test_mcp_error_routing(self):
        """Test routing of MCP errors."""
        error = MCPConnectionError("Connection failed")
        result = AdPerformanceErrorHandler.create_error_response(
            error=error,
            context="save_metrics",
        )

        assert result["status"] == "error"
        assert result["error_code"] == "3000"

    def test_ai_model_error_routing(self):
        """Test routing of AI model errors."""
        error = AIModelTimeoutError()
        result = AdPerformanceErrorHandler.create_error_response(
            error=error,
            context="generate_insights",
        )

        assert result["status"] == "error"
        assert result["error_code"] == "4002"

    def test_validation_error_routing(self):
        """Test routing of validation errors."""
        error = ValueError("Invalid input")
        result = AdPerformanceErrorHandler.create_error_response(
            error=error,
            context="validate_parameters",
        )

        assert result["status"] == "error"
        assert result["error_code"] == "1001"

    def test_unknown_error_routing(self):
        """Test routing of unknown errors."""
        error = RuntimeError("Unexpected error")
        result = AdPerformanceErrorHandler.create_error_response(
            error=error,
            context="unknown_operation",
        )

        assert result["status"] == "error"
        assert result["error_code"] == "1000"
        assert result["retry_allowed"] is False
        assert result["details"]["context"] == "unknown_operation"
        assert result["details"]["error_type"] == "RuntimeError"


class TestErrorResponseStandardization:
    """Test that all error responses follow the standard format."""

    def test_api_error_response_format(self):
        """Test API error response has all required fields."""
        error = RateLimitError(platform="meta", retry_after=60)
        result = AdPerformanceErrorHandler.handle_api_error(
            error=error,
            platform="meta",
            retry_count=0,
        )

        # Required fields
        assert "status" in result
        assert "error_code" in result
        assert "message" in result
        assert "retry_allowed" in result

        # Type checks
        assert isinstance(result["status"], str)
        assert isinstance(result["error_code"], str)
        assert isinstance(result["message"], str)
        assert isinstance(result["retry_allowed"], bool)

    def test_mcp_error_response_format(self):
        """Test MCP error response has all required fields."""
        error = MCPToolError(message="Tool failed", code="3003")
        result = AdPerformanceErrorHandler.handle_mcp_error(error)

        assert "status" in result
        assert "error_code" in result
        assert "message" in result
        assert "retry_allowed" in result

    def test_ai_error_response_format(self):
        """Test AI error response has all required fields."""
        error = AIModelQuotaError()
        result = AdPerformanceErrorHandler.handle_ai_model_error(error)

        assert "status" in result
        assert "error_code" in result
        assert "message" in result
        assert "retry_allowed" in result
