"""
Retry strategy for Campaign Automation module.

This module provides retry logic with exponential backoff for ad platform APIs,
MCP calls, and AI model interactions.

Requirements: 4.4, 9.1, 9.2, 9.3, 9.4, 9.5
"""

import asyncio
from typing import Any, Callable

import structlog

logger = structlog.get_logger(__name__)


class RetryStrategy:
    """
    Retry strategy with exponential backoff.

    Implements:
    - Exponential backoff: 1s, 2s, 4s
    - 30 second timeout for all operations
    - Maximum 3 retry attempts
    - Detailed error logging

    Requirements: 4.4, 9.1, 9.2, 9.4
    """

    # Retry configuration
    MAX_RETRIES = 3
    BASE_DELAY = 1  # seconds
    BACKOFF_FACTOR = 2  # exponential base
    TIMEOUT = 30  # seconds

    # Retryable error types
    RETRYABLE_ERRORS = [
        "CONNECTION_FAILED",
        "TIMEOUT",
        "API_RATE_LIMIT",
        "SERVICE_UNAVAILABLE",
        "AI_MODEL_FAILED",
        "PLATFORM_SERVICE_ERROR",
        "PLATFORM_TIMEOUT",
        "MCP_CONNECTION_ERROR",
        "MCP_TIMEOUT",
    ]

    @staticmethod
    async def retry_with_backoff(
        func: Callable,
        max_retries: int = MAX_RETRIES,
        timeout: int = TIMEOUT,
        context: str = "operation",
        **kwargs: Any,
    ) -> Any:
        """
        Execute a function with exponential backoff retry.

        Retry delays: 1s, 2s, 4s

        Args:
            func: Async function to execute
            max_retries: Maximum number of retry attempts (default 3)
            timeout: Timeout in seconds for each attempt (default 30)
            context: Context string for logging
            **kwargs: Additional arguments to pass to func

        Returns:
            Result from successful function call

        Raises:
            Last exception if all retries fail

        Requirements: 9.1, 9.2, 9.4
        """
        last_error = None

        for attempt in range(max_retries):
            try:
                # Execute with timeout
                result = await asyncio.wait_for(
                    func(**kwargs),
                    timeout=timeout,
                )
                return result

            except asyncio.TimeoutError as e:
                last_error = e
                error_type = "TIMEOUT"

                logger.warning(
                    "retry_timeout",
                    context=context,
                    attempt=attempt + 1,
                    max_retries=max_retries,
                    timeout=timeout,
                )

                if attempt < max_retries - 1:
                    delay = RetryStrategy.BASE_DELAY * (RetryStrategy.BACKOFF_FACTOR**attempt)
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        "retry_exhausted_timeout",
                        context=context,
                        attempts=max_retries,
                        timeout=timeout,
                    )

            except Exception as e:
                last_error = e
                error_type = getattr(e, "error_type", type(e).__name__)

                # Check if error is retryable
                if not RetryStrategy._is_retryable(error_type):
                    logger.warning(
                        "non_retryable_error",
                        context=context,
                        error_type=error_type,
                        error=str(e),
                    )
                    raise

                logger.warning(
                    "retry_attempt",
                    context=context,
                    attempt=attempt + 1,
                    max_retries=max_retries,
                    error_type=error_type,
                    error=str(e),
                )

                if attempt < max_retries - 1:
                    # Exponential backoff: 1s, 2s, 4s
                    delay = RetryStrategy.BASE_DELAY * (RetryStrategy.BACKOFF_FACTOR**attempt)
                    logger.info(
                        "retry_backoff",
                        context=context,
                        delay=delay,
                        next_attempt=attempt + 2,
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        "retry_exhausted",
                        context=context,
                        attempts=max_retries,
                        error_type=error_type,
                        error=str(e),
                    )

        # All retries failed
        if last_error:
            raise last_error

    @staticmethod
    def _is_retryable(error_type: str) -> bool:
        """
        Check if an error type is retryable.

        Args:
            error_type: Error type string

        Returns:
            True if error should trigger retry
        """
        return error_type in RetryStrategy.RETRYABLE_ERRORS

    @staticmethod
    def calculate_delay(attempt: int) -> float:
        """
        Calculate delay for a given attempt number.

        Uses exponential backoff: 1s, 2s, 4s

        Args:
            attempt: Attempt number (0-indexed)

        Returns:
            Delay in seconds
        """
        return RetryStrategy.BASE_DELAY * (RetryStrategy.BACKOFF_FACTOR**attempt)

    @staticmethod
    def log_retry_attempt(
        context: str,
        attempt: int,
        max_retries: int,
        error: Exception,
    ) -> None:
        """
        Log a retry attempt with detailed information.

        Args:
            context: Context string
            attempt: Current attempt number (1-indexed)
            max_retries: Maximum retry attempts
            error: The exception that triggered retry

        Requirements: 9.5
        """
        delay = RetryStrategy.calculate_delay(attempt - 1)

        logger.warning(
            "retry_operation",
            context=context,
            attempt=attempt,
            max_retries=max_retries,
            delay=delay,
            error_type=type(error).__name__,
            error_message=str(error),
            retryable=RetryStrategy._is_retryable(getattr(error, "error_type", type(error).__name__)),
        )

    @staticmethod
    def log_retry_exhausted(
        context: str,
        max_retries: int,
        error: Exception,
    ) -> None:
        """
        Log when all retry attempts are exhausted.

        Args:
            context: Context string
            max_retries: Maximum retry attempts
            error: The final exception

        Requirements: 9.5
        """
        logger.error(
            "retry_limit_reached",
            context=context,
            max_retries=max_retries,
            error_type=type(error).__name__,
            error_message=str(error),
            final_error=True,
        )

    @staticmethod
    def log_error(
        context: str,
        error: Exception,
        details: dict[str, Any] | None = None,
    ) -> None:
        """
        Log an error with detailed information.

        Args:
            context: Context string
            error: The exception
            details: Additional error details

        Requirements: 9.5
        """
        log_data = {
            "context": context,
            "error_type": type(error).__name__,
            "error_message": str(error),
        }

        if details:
            log_data.update(details)

        logger.error("operation_error", **log_data)


class TimeoutConfig:
    """
    Timeout configuration for different operations.

    Requirements: 9.2
    """

    # Default timeout for all operations
    DEFAULT_TIMEOUT = 30  # seconds

    # Specific timeouts for different operation types
    API_CALL_TIMEOUT = 30  # Ad platform API calls
    MCP_CALL_TIMEOUT = 30  # MCP tool calls
    AI_GENERATION_TIMEOUT = 30  # AI text generation

    @staticmethod
    def get_timeout(operation_type: str = "default") -> int:
        """
        Get timeout for a specific operation type.

        Args:
            operation_type: Type of operation (api_call, mcp_call, ai_generation, default)

        Returns:
            Timeout in seconds
        """
        timeouts = {
            "api_call": TimeoutConfig.API_CALL_TIMEOUT,
            "mcp_call": TimeoutConfig.MCP_CALL_TIMEOUT,
            "ai_generation": TimeoutConfig.AI_GENERATION_TIMEOUT,
            "default": TimeoutConfig.DEFAULT_TIMEOUT,
        }

        return timeouts.get(operation_type, TimeoutConfig.DEFAULT_TIMEOUT)
