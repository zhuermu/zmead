"""
Retry utilities for Ad Creative module.

Requirements: 4.5, 4.1.4, 10.5
- 4.5: Auto-retry image generation up to 3 times
- 4.1.4: Retry file upload up to 3 times
- 10.5: Retry MCP calls on failure

Wraps the core retry module with ad_creative specific configurations.
"""

import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

import structlog

from app.core.retry import (
    RetryConfig,
    RetryContext,
    calculate_backoff_delay,
    retry_async,
    retry_with_backoff,
)

logger = structlog.get_logger(__name__)

T = TypeVar("T")


# Ad Creative specific retry configurations
IMAGE_GENERATION_RETRY_CONFIG = RetryConfig(
    max_retries=3,
    base_delay=1.0,
    max_delay=30.0,
    exponential_base=2.0,
    jitter=True,
)

FILE_UPLOAD_RETRY_CONFIG = RetryConfig(
    max_retries=3,
    base_delay=1.0,
    max_delay=30.0,
    exponential_base=2.0,
    jitter=True,
)

MCP_CALL_RETRY_CONFIG = RetryConfig(
    max_retries=3,
    base_delay=1.0,
    max_delay=30.0,
    exponential_base=2.0,
    jitter=True,
)


class AdCreativeRetryError(Exception):
    """Error raised when all retries are exhausted."""

    def __init__(
        self,
        message: str,
        operation: str,
        attempts: int,
        last_error: Exception | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.operation = operation
        self.attempts = attempts
        self.last_error = last_error


def is_retryable_ad_creative_error(exception: Exception) -> bool:
    """Check if an exception is retryable for ad creative operations.

    Args:
        exception: The exception to check

    Returns:
        True if the exception should trigger a retry
    """
    # Import here to avoid circular imports
    from ..generators.image_generator import ImageGenerationError

    # Check for retryable attribute
    if hasattr(exception, "retryable"):
        return exception.retryable

    # Check for specific exception types
    retryable_types = (
        ConnectionError,
        TimeoutError,
        asyncio.TimeoutError,
        OSError,  # Network errors
    )

    if isinstance(exception, retryable_types):
        return True

    # Check for ImageGenerationError
    if isinstance(exception, ImageGenerationError):
        return exception.retryable

    # Check error message for common retryable patterns
    error_str = str(exception).lower()
    retryable_patterns = [
        "timeout",
        "connection",
        "rate limit",
        "503",
        "500",
        "unavailable",
        "temporary",
    ]

    return any(pattern in error_str for pattern in retryable_patterns)


async def retry_image_generation(
    func: Callable[[], Awaitable[T]],
    context: str = "image_generation",
) -> T:
    """Retry image generation with exponential backoff.

    Args:
        func: Async function to execute
        context: Context string for logging

    Returns:
        Result of the function

    Raises:
        AdCreativeRetryError: If all retries are exhausted
    """
    config = IMAGE_GENERATION_RETRY_CONFIG
    last_error: Exception | None = None

    for attempt in range(config.max_retries + 1):
        try:
            return await func()
        except Exception as e:
            last_error = e

            if not is_retryable_ad_creative_error(e):
                logger.warning(
                    "non_retryable_error",
                    context=context,
                    error_type=type(e).__name__,
                    error=str(e),
                )
                raise

            if attempt >= config.max_retries:
                logger.error(
                    "image_generation_retries_exhausted",
                    context=context,
                    attempts=attempt + 1,
                    error=str(e),
                )
                raise AdCreativeRetryError(
                    f"Image generation failed after {attempt + 1} attempts: {e}",
                    operation="image_generation",
                    attempts=attempt + 1,
                    last_error=e,
                )

            delay = calculate_backoff_delay(attempt, config)
            logger.warning(
                "image_generation_retry",
                context=context,
                attempt=attempt + 1,
                max_retries=config.max_retries,
                delay=round(delay, 2),
                error=str(e),
            )
            await asyncio.sleep(delay)

    # Should not reach here
    if last_error:
        raise last_error
    raise RuntimeError("Unexpected retry loop exit")


async def retry_file_upload(
    func: Callable[[], Awaitable[T]],
    context: str = "file_upload",
) -> T:
    """Retry file upload with exponential backoff.

    Args:
        func: Async function to execute
        context: Context string for logging

    Returns:
        Result of the function

    Raises:
        AdCreativeRetryError: If all retries are exhausted
    """
    config = FILE_UPLOAD_RETRY_CONFIG
    last_error: Exception | None = None

    for attempt in range(config.max_retries + 1):
        try:
            return await func()
        except Exception as e:
            last_error = e

            if not is_retryable_ad_creative_error(e):
                logger.warning(
                    "non_retryable_upload_error",
                    context=context,
                    error_type=type(e).__name__,
                    error=str(e),
                )
                raise

            if attempt >= config.max_retries:
                logger.error(
                    "file_upload_retries_exhausted",
                    context=context,
                    attempts=attempt + 1,
                    error=str(e),
                )
                raise AdCreativeRetryError(
                    f"File upload failed after {attempt + 1} attempts: {e}",
                    operation="file_upload",
                    attempts=attempt + 1,
                    last_error=e,
                )

            delay = calculate_backoff_delay(attempt, config)
            logger.warning(
                "file_upload_retry",
                context=context,
                attempt=attempt + 1,
                max_retries=config.max_retries,
                delay=round(delay, 2),
                error=str(e),
            )
            await asyncio.sleep(delay)

    if last_error:
        raise last_error
    raise RuntimeError("Unexpected retry loop exit")


async def retry_mcp_call(
    func: Callable[[], Awaitable[T]],
    context: str = "mcp_call",
) -> T:
    """Retry MCP tool call with exponential backoff.

    Args:
        func: Async function to execute
        context: Context string for logging

    Returns:
        Result of the function

    Raises:
        AdCreativeRetryError: If all retries are exhausted
    """
    config = MCP_CALL_RETRY_CONFIG
    last_error: Exception | None = None

    for attempt in range(config.max_retries + 1):
        try:
            return await func()
        except Exception as e:
            last_error = e

            if not is_retryable_ad_creative_error(e):
                logger.warning(
                    "non_retryable_mcp_error",
                    context=context,
                    error_type=type(e).__name__,
                    error=str(e),
                )
                raise

            if attempt >= config.max_retries:
                logger.error(
                    "mcp_call_retries_exhausted",
                    context=context,
                    attempts=attempt + 1,
                    error=str(e),
                )
                raise AdCreativeRetryError(
                    f"MCP call failed after {attempt + 1} attempts: {e}",
                    operation="mcp_call",
                    attempts=attempt + 1,
                    last_error=e,
                )

            delay = calculate_backoff_delay(attempt, config)
            logger.warning(
                "mcp_call_retry",
                context=context,
                attempt=attempt + 1,
                max_retries=config.max_retries,
                delay=round(delay, 2),
                error=str(e),
            )
            await asyncio.sleep(delay)

    if last_error:
        raise last_error
    raise RuntimeError("Unexpected retry loop exit")


# Re-export core retry utilities for convenience
__all__ = [
    "AdCreativeRetryError",
    "IMAGE_GENERATION_RETRY_CONFIG",
    "FILE_UPLOAD_RETRY_CONFIG",
    "MCP_CALL_RETRY_CONFIG",
    "is_retryable_ad_creative_error",
    "retry_image_generation",
    "retry_file_upload",
    "retry_mcp_call",
    # Re-exports from core
    "RetryConfig",
    "RetryContext",
    "calculate_backoff_delay",
    "retry_async",
    "retry_with_backoff",
]
