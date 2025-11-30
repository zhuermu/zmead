"""
Retry strategy for Market Insights module.

Provides retry logic with exponential backoff for third-party API calls
(TikTok Creative Center, pytrends) and AI model interactions.

Requirements: 6.3, 6.5
"""

import asyncio
from typing import Any, Callable, TypeVar

import structlog

logger = structlog.get_logger(__name__)

T = TypeVar("T")


class RetryableError(Exception):
    """Base exception for retryable errors."""
    
    def __init__(self, message: str, error_type: str = "UNKNOWN"):
        super().__init__(message)
        self.error_type = error_type


class TimeoutError(RetryableError):
    """Timeout error for API calls."""
    
    def __init__(self, message: str = "Operation timed out"):
        super().__init__(message, error_type="TIMEOUT")


class RateLimitError(RetryableError):
    """Rate limit exceeded error."""
    
    def __init__(self, message: str = "Rate limit exceeded", retry_after: int = 60):
        super().__init__(message, error_type="RATE_LIMIT")
        self.retry_after = retry_after


class APIError(RetryableError):
    """Generic API error."""
    
    def __init__(self, message: str, status_code: int | None = None):
        error_type = "API_ERROR"
        if status_code:
            if status_code == 429:
                error_type = "RATE_LIMIT"
            elif status_code >= 500:
                error_type = "SERVICE_UNAVAILABLE"
        super().__init__(message, error_type=error_type)
        self.status_code = status_code


async def retry_with_backoff(
    func: Callable[..., Any],
    max_retries: int = 3,
    backoff_factor: int = 2,
    timeout: int = 30,
    context: str = "operation",
    retryable_errors: tuple[type[Exception], ...] | None = None,
    **kwargs: Any,
) -> Any:
    """Execute a function with exponential backoff retry.
    
    Implements retry logic with:
    - Maximum 3 retries (configurable)
    - Exponential backoff: 1s, 2s, 4s (base * factor^attempt)
    - 30 second timeout per attempt (configurable)
    
    Args:
        func: Async function to execute
        max_retries: Maximum number of retry attempts (default: 3)
        backoff_factor: Multiplier for exponential backoff (default: 2)
        timeout: Timeout in seconds for each attempt (default: 30)
        context: Context string for logging
        retryable_errors: Tuple of exception types to retry on
        **kwargs: Arguments to pass to func
        
    Returns:
        Result from successful function call
        
    Raises:
        Last exception if all retries fail
        
    Requirements: 6.3, 6.5
    """
    if retryable_errors is None:
        retryable_errors = (
            RetryableError,
            asyncio.TimeoutError,
            ConnectionError,
            OSError,
        )
    
    last_error: Exception | None = None
    base_delay = 1  # 1 second base delay
    
    for attempt in range(max_retries):
        log = logger.bind(
            context=context,
            attempt=attempt + 1,
            max_retries=max_retries,
        )
        
        try:
            # Execute with timeout
            result = await asyncio.wait_for(
                func(**kwargs) if kwargs else func(),
                timeout=timeout,
            )
            
            if attempt > 0:
                log.info("retry_succeeded")
            
            return result
            
        except asyncio.TimeoutError as e:
            last_error = TimeoutError(f"Operation timed out after {timeout}s")
            log.warning(
                "retry_timeout",
                timeout=timeout,
            )
            
        except retryable_errors as e:
            last_error = e
            error_type = getattr(e, "error_type", type(e).__name__)
            log.warning(
                "retry_error",
                error_type=error_type,
                error=str(e),
            )
            
        except Exception as e:
            # Non-retryable error - raise immediately
            log.error(
                "non_retryable_error",
                error_type=type(e).__name__,
                error=str(e),
            )
            raise
        
        # Calculate backoff delay
        if attempt < max_retries - 1:
            delay = base_delay * (backoff_factor ** attempt)
            log.info(
                "retry_backoff",
                delay_seconds=delay,
                next_attempt=attempt + 2,
            )
            await asyncio.sleep(delay)
        else:
            log.error(
                "retry_exhausted",
                total_attempts=max_retries,
            )
    
    # All retries failed
    if last_error:
        raise last_error
    
    raise RuntimeError(f"Retry failed for {context}")


class RetryStrategy:
    """Retry strategy with configurable parameters.
    
    Provides a class-based interface for retry logic with
    exponential backoff.
    
    Requirements: 6.3, 6.5
    """
    
    # Default configuration
    MAX_RETRIES = 3
    BASE_DELAY = 1  # seconds
    BACKOFF_FACTOR = 2
    TIMEOUT = 30  # seconds
    
    # Retryable error types
    RETRYABLE_ERROR_TYPES = [
        "TIMEOUT",
        "RATE_LIMIT",
        "SERVICE_UNAVAILABLE",
        "CONNECTION_FAILED",
        "API_ERROR",
    ]
    
    def __init__(
        self,
        max_retries: int | None = None,
        timeout: int | None = None,
        backoff_factor: int | None = None,
    ):
        """Initialize retry strategy.
        
        Args:
            max_retries: Maximum retry attempts
            timeout: Timeout per attempt in seconds
            backoff_factor: Exponential backoff multiplier
        """
        self.max_retries = max_retries or self.MAX_RETRIES
        self.timeout = timeout or self.TIMEOUT
        self.backoff_factor = backoff_factor or self.BACKOFF_FACTOR
    
    async def execute(
        self,
        func: Callable[..., Any],
        context: str = "operation",
        **kwargs: Any,
    ) -> Any:
        """Execute function with retry logic.
        
        Args:
            func: Async function to execute
            context: Context for logging
            **kwargs: Arguments to pass to func
            
        Returns:
            Result from successful execution
            
        Raises:
            Last exception if all retries fail
        """
        return await retry_with_backoff(
            func=func,
            max_retries=self.max_retries,
            backoff_factor=self.backoff_factor,
            timeout=self.timeout,
            context=context,
            **kwargs,
        )
    
    @staticmethod
    def calculate_delay(attempt: int, backoff_factor: int = 2) -> float:
        """Calculate delay for a given attempt.
        
        Args:
            attempt: Attempt number (0-indexed)
            backoff_factor: Exponential backoff multiplier
            
        Returns:
            Delay in seconds
        """
        return 1 * (backoff_factor ** attempt)
    
    @staticmethod
    def is_retryable(error: Exception) -> bool:
        """Check if an error is retryable.
        
        Args:
            error: Exception to check
            
        Returns:
            True if error should trigger retry
        """
        if isinstance(error, RetryableError):
            return True
        if isinstance(error, (asyncio.TimeoutError, ConnectionError, OSError)):
            return True
        
        error_type = getattr(error, "error_type", None)
        if error_type and error_type in RetryStrategy.RETRYABLE_ERROR_TYPES:
            return True
        
        return False


class TimeoutConfig:
    """Timeout configuration for different operations.
    
    Requirements: 6.5
    """
    
    # Default timeout for all operations
    DEFAULT_TIMEOUT = 30  # seconds
    
    # Specific timeouts for different operation types
    TIKTOK_API_TIMEOUT = 30
    PYTRENDS_TIMEOUT = 30
    AI_ANALYSIS_TIMEOUT = 45  # AI operations may take longer
    COMPETITOR_ANALYSIS_TIMEOUT = 60  # Web scraping may be slower
    
    @staticmethod
    def get_timeout(operation_type: str = "default") -> int:
        """Get timeout for a specific operation type.
        
        Args:
            operation_type: Type of operation
            
        Returns:
            Timeout in seconds
        """
        timeouts = {
            "tiktok_api": TimeoutConfig.TIKTOK_API_TIMEOUT,
            "pytrends": TimeoutConfig.PYTRENDS_TIMEOUT,
            "ai_analysis": TimeoutConfig.AI_ANALYSIS_TIMEOUT,
            "competitor_analysis": TimeoutConfig.COMPETITOR_ANALYSIS_TIMEOUT,
            "default": TimeoutConfig.DEFAULT_TIMEOUT,
        }
        return timeouts.get(operation_type, TimeoutConfig.DEFAULT_TIMEOUT)
