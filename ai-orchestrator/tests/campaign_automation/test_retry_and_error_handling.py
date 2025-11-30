"""
Tests for retry strategy and error handling in Campaign Automation module.

Requirements: 4.4, 9.1, 9.2, 9.3, 9.4, 9.5
"""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.modules.campaign_automation.utils.error_handler import (
    AdPlatformError,
    BudgetInsufficientError,
    CampaignAutomationErrorHandler,
    CreativeRejectedError,
    ErrorResponseFormatter,
    PermissionDeniedError,
    PlatformServiceError,
    PlatformTimeoutError,
    RateLimitError,
    TokenExpiredError,
    TokenInvalidError,
)
from app.modules.campaign_automation.utils.retry_strategy import (
    RetryStrategy,
    TimeoutConfig,
)


class TestRetryStrategy:
    """Test RetryStrategy class"""

    @pytest.mark.asyncio
    async def test_retry_with_backoff_success_first_attempt(self):
        """Test successful execution on first attempt"""
        # Setup
        mock_func = AsyncMock(return_value="success")

        # Execute
        result = await RetryStrategy.retry_with_backoff(
            func=mock_func,
            context="test_operation",
        )

        # Verify
        assert result == "success"
        assert mock_func.call_count == 1

    @pytest.mark.asyncio
    async def test_retry_with_backoff_success_after_retries(self):
        """Test successful execution after retries"""
        # Setup
        error1 = Exception("First failure")
        error1.error_type = "CONNECTION_FAILED"
        error2 = Exception("Second failure")
        error2.error_type = "CONNECTION_FAILED"
        
        mock_func = AsyncMock(
            side_effect=[
                error1,
                error2,
                "success",
            ]
        )

        # Execute
        result = await RetryStrategy.retry_with_backoff(
            func=mock_func,
            context="test_operation",
        )

        # Verify
        assert result == "success"
        assert mock_func.call_count == 3

    @pytest.mark.asyncio
    async def test_retry_with_backoff_timeout(self):
        """Test timeout handling"""
        # Setup
        async def slow_func():
            await asyncio.sleep(2)
            return "success"

        # Execute & Verify
        with pytest.raises(asyncio.TimeoutError):
            await RetryStrategy.retry_with_backoff(
                func=slow_func,
                timeout=0.1,
                context="test_operation",
            )

    @pytest.mark.asyncio
    async def test_retry_with_backoff_exhausted(self):
        """Test retry exhaustion"""
        # Setup
        error = Exception("Persistent failure")
        error.error_type = "CONNECTION_FAILED"
        mock_func = AsyncMock(side_effect=error)

        # Execute & Verify
        with pytest.raises(Exception, match="Persistent failure"):
            await RetryStrategy.retry_with_backoff(
                func=mock_func,
                max_retries=3,
                context="test_operation",
            )

        # Should have tried 3 times
        assert mock_func.call_count == 3

    @pytest.mark.asyncio
    async def test_retry_with_backoff_non_retryable_error(self):
        """Test non-retryable error is not retried"""
        # Setup
        error = ValueError("Invalid input")
        error.error_type = "VALIDATION_ERROR"
        mock_func = AsyncMock(side_effect=error)

        # Execute & Verify
        with pytest.raises(ValueError, match="Invalid input"):
            await RetryStrategy.retry_with_backoff(
                func=mock_func,
                context="test_operation",
            )

        # Should only try once
        assert mock_func.call_count == 1

    def test_calculate_delay(self):
        """Test exponential backoff delay calculation"""
        # Verify delays: 1s, 2s, 4s
        assert RetryStrategy.calculate_delay(0) == 1
        assert RetryStrategy.calculate_delay(1) == 2
        assert RetryStrategy.calculate_delay(2) == 4

    def test_is_retryable(self):
        """Test retryable error detection"""
        # Retryable errors
        assert RetryStrategy._is_retryable("CONNECTION_FAILED")
        assert RetryStrategy._is_retryable("TIMEOUT")
        assert RetryStrategy._is_retryable("API_RATE_LIMIT")
        assert RetryStrategy._is_retryable("SERVICE_UNAVAILABLE")

        # Non-retryable errors
        assert not RetryStrategy._is_retryable("VALIDATION_ERROR")
        assert not RetryStrategy._is_retryable("UNKNOWN_ERROR")


class TestTimeoutConfig:
    """Test TimeoutConfig class"""

    def test_get_timeout_default(self):
        """Test default timeout"""
        assert TimeoutConfig.get_timeout() == 30
        assert TimeoutConfig.get_timeout("default") == 30

    def test_get_timeout_specific(self):
        """Test specific operation timeouts"""
        assert TimeoutConfig.get_timeout("api_call") == 30
        assert TimeoutConfig.get_timeout("mcp_call") == 30
        assert TimeoutConfig.get_timeout("ai_generation") == 30

    def test_get_timeout_unknown(self):
        """Test unknown operation type returns default"""
        assert TimeoutConfig.get_timeout("unknown_operation") == 30


class TestErrorResponseFormatter:
    """Test ErrorResponseFormatter class"""

    def test_format_ad_platform_error(self):
        """Test formatting ad platform error"""
        # Setup
        error = TokenExpiredError(platform="meta", message="Token expired")

        # Execute
        response = ErrorResponseFormatter.format_error_response(
            error=error,
            context="create_campaign",
            platform="meta",
            retry_count=0,
        )

        # Verify
        assert response["status"] == "error"
        assert response["error"]["code"] == "6001"
        assert response["error"]["type"] == "TOKEN_EXPIRED"
        assert response["error"]["platform"] == "meta"
        assert response["error"]["context"] == "create_campaign"
        assert "timestamp" in response["error"]

    def test_format_rate_limit_error(self):
        """Test formatting rate limit error"""
        # Setup
        error = RateLimitError(platform="meta", retry_after=60)

        # Execute
        response = ErrorResponseFormatter.format_error_response(
            error=error,
            context="api_call",
            platform="meta",
            retry_count=1,
        )

        # Verify
        assert response["status"] == "error"
        assert response["error"]["code"] == "1003"
        assert response["error"]["type"] == "API_RATE_LIMIT"
        assert response["retry_after"] == 60
        assert response["error"]["details"]["retry_after"] == 60

    def test_format_error_retry_allowed(self):
        """Test retry_allowed flag"""
        # Setup
        error = PlatformServiceError(platform="meta", status_code=500)

        # Execute - first retry
        response1 = ErrorResponseFormatter.format_error_response(
            error=error,
            context="api_call",
            platform="meta",
            retry_count=0,
        )

        # Execute - max retries reached
        response2 = ErrorResponseFormatter.format_error_response(
            error=error,
            context="api_call",
            platform="meta",
            retry_count=3,
        )

        # Verify
        assert response1["retry_allowed"] is True
        assert response2["retry_allowed"] is False


class TestCampaignAutomationErrorHandler:
    """Test CampaignAutomationErrorHandler class"""

    def test_handle_token_expired_error(self):
        """Test handling token expired error"""
        # Setup
        error = TokenExpiredError(platform="meta")

        # Execute
        response = CampaignAutomationErrorHandler.handle_api_error(
            error=error,
            platform="meta",
            retry_count=0,
            context="create_campaign",
        )

        # Verify
        assert response["status"] == "error"
        assert response["error"]["code"] == "6001"
        assert response["error"]["type"] == "TOKEN_EXPIRED"

    def test_handle_rate_limit_error(self):
        """Test handling rate limit error"""
        # Setup
        error = RateLimitError(platform="meta", retry_after=120)

        # Execute
        response = CampaignAutomationErrorHandler.handle_api_error(
            error=error,
            platform="meta",
            retry_count=0,
            context="api_call",
        )

        # Verify
        assert response["status"] == "error"
        assert response["error"]["code"] == "1003"
        assert response["retry_after"] == 120

    def test_handle_platform_service_error(self):
        """Test handling platform service error"""
        # Setup
        error = PlatformServiceError(platform="meta", status_code=503)

        # Execute
        response = CampaignAutomationErrorHandler.handle_api_error(
            error=error,
            platform="meta",
            retry_count=0,
            context="api_call",
        )

        # Verify
        assert response["status"] == "error"
        assert response["error"]["code"] == "4002"
        assert response["error"]["details"]["status_code"] == 503

    def test_handle_budget_insufficient_error(self):
        """Test handling budget insufficient error"""
        # Setup
        error = BudgetInsufficientError(platform="meta")

        # Execute
        response = CampaignAutomationErrorHandler.handle_api_error(
            error=error,
            platform="meta",
            retry_count=0,
            context="create_campaign",
        )

        # Verify
        assert response["status"] == "error"
        assert response["error"]["code"] == "6002"
        assert response["error"]["type"] == "BUDGET_INSUFFICIENT"

    def test_handle_creative_rejected_error(self):
        """Test handling creative rejected error"""
        # Setup
        error = CreativeRejectedError(platform="meta", reason="Policy violation")

        # Execute
        response = CampaignAutomationErrorHandler.handle_api_error(
            error=error,
            platform="meta",
            retry_count=0,
            context="create_ad",
        )

        # Verify
        assert response["status"] == "error"
        assert response["error"]["code"] == "6003"
        assert response["error"]["details"]["reason"] == "Policy violation"

    def test_handle_validation_error(self):
        """Test handling validation error"""
        # Setup
        error = ValueError("Invalid budget value")

        # Execute
        response = CampaignAutomationErrorHandler.handle_validation_error(
            error=error,
            field="daily_budget",
            context="create_campaign",
        )

        # Verify
        assert response["status"] == "error"
        assert response["error"]["code"] == "1001"
        assert response["error"]["type"] == "VALIDATION_ERROR"
        assert response["error"]["details"]["field"] == "daily_budget"
        assert response["retry_allowed"] is False

    def test_create_error_response_routes_correctly(self):
        """Test create_error_response routes to correct handler"""
        # Test ad platform error
        ad_error = TokenExpiredError(platform="meta")
        response1 = CampaignAutomationErrorHandler.create_error_response(
            error=ad_error,
            context="test",
            platform="meta",
        )
        assert response1["error"]["type"] == "TOKEN_EXPIRED"

        # Test validation error
        val_error = ValueError("Invalid input")
        response2 = CampaignAutomationErrorHandler.create_error_response(
            error=val_error,
            context="test",
        )
        assert response2["error"]["type"] == "VALIDATION_ERROR"

    @pytest.mark.asyncio
    async def test_retry_with_backoff_method(self):
        """Test retry_with_backoff method"""
        # Setup
        mock_func = AsyncMock(
            side_effect=[
                PlatformTimeoutError(platform="meta"),
                "success",
            ]
        )

        # Execute
        result = await CampaignAutomationErrorHandler.retry_with_backoff(
            func=mock_func,
            max_retries=3,
            timeout=30,
            context="test_operation",
        )

        # Verify
        assert result == "success"
        assert mock_func.call_count == 2


class TestAdPlatformErrors:
    """Test ad platform error classes"""

    def test_token_expired_error(self):
        """Test TokenExpiredError"""
        error = TokenExpiredError(platform="meta")
        assert error.platform == "meta"
        assert error.code == "6001"
        assert error.error_type == "TOKEN_EXPIRED"

    def test_token_invalid_error(self):
        """Test TokenInvalidError"""
        error = TokenInvalidError(platform="tiktok")
        assert error.platform == "tiktok"
        assert error.code == "6001"
        assert error.error_type == "TOKEN_INVALID"

    def test_permission_denied_error(self):
        """Test PermissionDeniedError"""
        error = PermissionDeniedError(platform="google")
        assert error.platform == "google"
        assert error.code == "6001"
        assert error.error_type == "PERMISSION_DENIED"

    def test_rate_limit_error(self):
        """Test RateLimitError"""
        error = RateLimitError(platform="meta", retry_after=120)
        assert error.platform == "meta"
        assert error.code == "1003"
        assert error.retry_after == 120
        assert error.error_type == "API_RATE_LIMIT"

    def test_platform_service_error(self):
        """Test PlatformServiceError"""
        error = PlatformServiceError(platform="meta", status_code=503)
        assert error.platform == "meta"
        assert error.code == "4002"
        assert error.details["status_code"] == 503
        assert error.error_type == "PLATFORM_SERVICE_ERROR"

    def test_platform_timeout_error(self):
        """Test PlatformTimeoutError"""
        error = PlatformTimeoutError(platform="meta")
        assert error.platform == "meta"
        assert error.code == "4002"
        assert error.error_type == "PLATFORM_TIMEOUT"

    def test_budget_insufficient_error(self):
        """Test BudgetInsufficientError"""
        error = BudgetInsufficientError(platform="meta")
        assert error.platform == "meta"
        assert error.code == "6002"
        assert error.error_type == "BUDGET_INSUFFICIENT"

    def test_creative_rejected_error(self):
        """Test CreativeRejectedError"""
        error = CreativeRejectedError(platform="meta", reason="Policy violation")
        assert error.platform == "meta"
        assert error.code == "6003"
        assert error.details["reason"] == "Policy violation"
        assert error.error_type == "CREATIVE_REJECTED"

    def test_ad_platform_error_base(self):
        """Test AdPlatformError base class"""
        error = AdPlatformError(
            message="Test error",
            platform="meta",
            code="9999",
            details={"key": "value"},
        )
        assert error.message == "Test error"
        assert error.platform == "meta"
        assert error.code == "9999"
        assert error.details["key"] == "value"
        assert error.error_type == "AD_PLATFORM_ERROR"
