"""Retry logic with exponential backoff for AI Orchestrator.

This module provides a decorator and utilities for retrying operations
with exponential backoff and jitter to prevent thundering herd.

Requirements: 需求 11.4
"""

import asyncio
import functools
import random
from collections.abc import Awaitable, Callable
from typing import ParamSpec, TypeVar

import structlog

logger = structlog.get_logger(__name__)

P = ParamSpec("P")
T = TypeVar("T")


class RetryConfig:
    """Configuration for retry behavior."""

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        jitter_factor: float = 0.5,
    ):
        """Initialize retry configuration.

        Args:
            max_retries: Maximum number of retry attempts (default 3)
            base_delay: Base delay in seconds (default 1.0)
            max_delay: Maximum delay cap in seconds (default 60.0)
            exponential_base: Base for exponential calculation (default 2.0)
            jitter: Whether to add random jitter (default True)
            jitter_factor: Factor for jitter range (default 0.5)
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.jitter_factor = jitter_factor


# Default configuration: 1s, 2s, 4s backoff
DEFAULT_RETRY_CONFIG = RetryConfig(
    max_retries=3,
    base_delay=1.0,
    exponential_base=2.0,
)


def calculate_backoff_delay(
    attempt: int,
    config: RetryConfig,
) -> float:
    """Calculate the delay before the next retry attempt.

    Uses exponential backoff with optional jitter.

    Args:
        attempt: Current attempt number (0-indexed)
        config: Retry configuration

    Returns:
        Delay in seconds before next retry
    """
    # Calculate exponential delay: base_delay * (exponential_base ^ attempt)
    # For default config: 1s, 2s, 4s
    delay = config.base_delay * (config.exponential_base**attempt)

    # Cap at max delay
    delay = min(delay, config.max_delay)

    # Add jitter to prevent thundering herd
    if config.jitter:
        # Jitter range: [delay * (1 - jitter_factor), delay * (1 + jitter_factor)]
        jitter_range = delay * config.jitter_factor
        delay = delay + random.uniform(-jitter_range, jitter_range)
        # Ensure delay is positive
        delay = max(0.1, delay)

    return delay


def is_retryable_exception(
    exception: Exception,
    retryable_exceptions: tuple[type[Exception], ...] | None = None,
) -> bool:
    """Check if an exception is retryable.

    Args:
        exception: The exception to check
        retryable_exceptions: Tuple of exception types that are retryable

    Returns:
        True if the exception should trigger a retry
    """
    if retryable_exceptions is None:
        # Default retryable exceptions
        from app.core.errors import AIModelTimeoutError
        from app.services.mcp_client import (
            MCPConnectionError,
            MCPTimeoutError,
        )

        retryable_exceptions = (
            MCPConnectionError,
            MCPTimeoutError,
            AIModelTimeoutError,
            ConnectionError,
            TimeoutError,
            asyncio.TimeoutError,
        )

    return isinstance(exception, retryable_exceptions)


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    exponential_base: float = 2.0,
    max_delay: float = 60.0,
    jitter: bool = True,
    retryable_exceptions: tuple[type[Exception], ...] | None = None,
    on_retry: Callable[[int, Exception, float], None] | None = None,
) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T]]]:
    """Decorator for retrying async functions with exponential backoff.

    Implements exponential backoff with jitter to prevent thundering herd.
    Default backoff: 1s, 2s, 4s (with jitter).

    Args:
        max_retries: Maximum number of retry attempts (default 3)
        base_delay: Base delay in seconds (default 1.0)
        exponential_base: Base for exponential calculation (default 2.0)
        max_delay: Maximum delay cap in seconds (default 60.0)
        jitter: Whether to add random jitter (default True)
        retryable_exceptions: Tuple of exception types to retry on
        on_retry: Optional callback called before each retry

    Returns:
        Decorated function with retry logic

    Example:
        @retry_with_backoff(max_retries=3)
        async def call_external_service():
            ...
    """
    config = RetryConfig(
        max_retries=max_retries,
        base_delay=base_delay,
        max_delay=max_delay,
        exponential_base=exponential_base,
        jitter=jitter,
    )

    def decorator(func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            last_exception: Exception | None = None

            for attempt in range(max_retries + 1):  # +1 for initial attempt
                try:
                    return await func(*args, **kwargs)

                except Exception as e:
                    last_exception = e

                    # Check if we should retry
                    if not is_retryable_exception(e, retryable_exceptions):
                        logger.warning(
                            "non_retryable_exception",
                            function=func.__name__,
                            error_type=type(e).__name__,
                            error=str(e),
                        )
                        raise

                    # Check if we've exhausted retries
                    if attempt >= max_retries:
                        logger.error(
                            "max_retries_exceeded",
                            function=func.__name__,
                            max_retries=max_retries,
                            error_type=type(e).__name__,
                            error=str(e),
                        )
                        raise

                    # Calculate delay
                    delay = calculate_backoff_delay(attempt, config)

                    # Log retry attempt
                    logger.warning(
                        "retry_attempt",
                        function=func.__name__,
                        attempt=attempt + 1,
                        max_retries=max_retries,
                        wait_time=round(delay, 2),
                        error_type=type(e).__name__,
                        error=str(e),
                    )

                    # Call optional callback
                    if on_retry:
                        on_retry(attempt + 1, e, delay)

                    # Wait before retry
                    await asyncio.sleep(delay)

            # This should never be reached, but just in case
            if last_exception:
                raise last_exception
            raise RuntimeError("Unexpected retry loop exit")

        return wrapper

    return decorator


async def retry_async(
    func: Callable[[], Awaitable[T]],
    max_retries: int = 3,
    base_delay: float = 1.0,
    exponential_base: float = 2.0,
    max_delay: float = 60.0,
    jitter: bool = True,
    retryable_exceptions: tuple[type[Exception], ...] | None = None,
    context: str | None = None,
) -> T:
    """Execute an async function with retry logic.

    This is a functional alternative to the decorator for cases where
    you need more control over the retry behavior.

    Args:
        func: Async function to execute (no arguments)
        max_retries: Maximum number of retry attempts (default 3)
        base_delay: Base delay in seconds (default 1.0)
        exponential_base: Base for exponential calculation (default 2.0)
        max_delay: Maximum delay cap in seconds (default 60.0)
        jitter: Whether to add random jitter (default True)
        retryable_exceptions: Tuple of exception types to retry on
        context: Optional context string for logging

    Returns:
        Result of the function

    Raises:
        The original exception after max retries exceeded

    Example:
        result = await retry_async(
            lambda: mcp_client.call_tool("check_credit", params),
            max_retries=3,
            context="credit_check"
        )
    """
    config = RetryConfig(
        max_retries=max_retries,
        base_delay=base_delay,
        max_delay=max_delay,
        exponential_base=exponential_base,
        jitter=jitter,
    )

    last_exception: Exception | None = None
    log_context = context or "retry_async"

    for attempt in range(max_retries + 1):
        try:
            return await func()

        except Exception as e:
            last_exception = e

            # Check if we should retry
            if not is_retryable_exception(e, retryable_exceptions):
                logger.warning(
                    "non_retryable_exception",
                    context=log_context,
                    error_type=type(e).__name__,
                    error=str(e),
                )
                raise

            # Check if we've exhausted retries
            if attempt >= max_retries:
                logger.error(
                    "max_retries_exceeded",
                    context=log_context,
                    max_retries=max_retries,
                    error_type=type(e).__name__,
                    error=str(e),
                )
                raise

            # Calculate delay
            delay = calculate_backoff_delay(attempt, config)

            # Log retry attempt
            logger.warning(
                "retry_attempt",
                context=log_context,
                attempt=attempt + 1,
                max_retries=max_retries,
                wait_time=round(delay, 2),
                error_type=type(e).__name__,
                error=str(e),
            )

            # Wait before retry
            await asyncio.sleep(delay)

    # This should never be reached
    if last_exception:
        raise last_exception
    raise RuntimeError("Unexpected retry loop exit")


class RetryContext:
    """Context manager for tracking retry state.

    Useful for manual retry loops where you need to track
    attempt count and calculate delays.

    Example:
        retry_ctx = RetryContext(max_retries=3)
        while retry_ctx.should_retry():
            try:
                result = await some_operation()
                break
            except RetryableError as e:
                await retry_ctx.wait_before_retry(e)
    """

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        exponential_base: float = 2.0,
        max_delay: float = 60.0,
        jitter: bool = True,
        context: str | None = None,
    ):
        """Initialize retry context.

        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Base delay in seconds
            exponential_base: Base for exponential calculation
            max_delay: Maximum delay cap in seconds
            jitter: Whether to add random jitter
            context: Optional context string for logging
        """
        self.config = RetryConfig(
            max_retries=max_retries,
            base_delay=base_delay,
            max_delay=max_delay,
            exponential_base=exponential_base,
            jitter=jitter,
        )
        self.context = context or "retry_context"
        self.attempt = 0
        self.last_exception: Exception | None = None

    def should_retry(self) -> bool:
        """Check if another retry attempt should be made.

        Returns:
            True if more retries are available
        """
        return self.attempt <= self.config.max_retries

    def record_attempt(self, exception: Exception | None = None) -> None:
        """Record an attempt (successful or failed).

        Args:
            exception: The exception if the attempt failed
        """
        self.last_exception = exception
        self.attempt += 1

    def get_delay(self) -> float:
        """Get the delay before the next retry.

        Returns:
            Delay in seconds
        """
        # Use attempt - 1 because we've already incremented
        return calculate_backoff_delay(self.attempt - 1, self.config)

    async def wait_before_retry(self, exception: Exception) -> None:
        """Wait before the next retry attempt.

        Records the failed attempt and waits the appropriate delay.

        Args:
            exception: The exception that caused the retry

        Raises:
            The exception if max retries exceeded
        """
        self.record_attempt(exception)

        if not self.should_retry():
            logger.error(
                "max_retries_exceeded",
                context=self.context,
                max_retries=self.config.max_retries,
                error_type=type(exception).__name__,
                error=str(exception),
            )
            raise exception

        delay = self.get_delay()

        logger.warning(
            "retry_attempt",
            context=self.context,
            attempt=self.attempt,
            max_retries=self.config.max_retries,
            wait_time=round(delay, 2),
            error_type=type(exception).__name__,
            error=str(exception),
        )

        await asyncio.sleep(delay)

    @property
    def attempts_remaining(self) -> int:
        """Get the number of retry attempts remaining.

        Returns:
            Number of remaining attempts
        """
        return max(0, self.config.max_retries - self.attempt + 1)
