"""
Retry strategy for Landing Page module.

This module provides retry decorators and utilities for handling
transient failures with exponential backoff.
"""

import asyncio
import functools
import logging
from typing import Any, Callable, Optional, Type, Tuple

logger = logging.getLogger(__name__)


class RetryStrategy:
    """Retry strategy with exponential backoff"""
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 2.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0
    ):
        """
        Initialize retry strategy
        
        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Initial delay in seconds
            max_delay: Maximum delay in seconds
            exponential_base: Base for exponential backoff calculation
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
    
    def calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay for given attempt using exponential backoff
        
        Args:
            attempt: Current attempt number (0-indexed)
        
        Returns:
            Delay in seconds
        """
        delay = self.base_delay * (self.exponential_base ** attempt)
        return min(delay, self.max_delay)
    
    async def execute_with_retry(
        self,
        func: Callable,
        *args,
        retryable_exceptions: Optional[Tuple[Type[Exception], ...]] = None,
        **kwargs
    ) -> Any:
        """
        Execute a function with retry logic
        
        Args:
            func: The async function to execute
            *args: Positional arguments for the function
            retryable_exceptions: Tuple of exception types to retry on
            **kwargs: Keyword arguments for the function
        
        Returns:
            Result of the function
        
        Raises:
            The last exception if all retries fail
        """
        if retryable_exceptions is None:
            retryable_exceptions = (
                ConnectionError,
                TimeoutError,
                asyncio.TimeoutError,
            )
        
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                result = await func(*args, **kwargs)
                
                if attempt > 0:
                    logger.info(
                        f"Function {func.__name__} succeeded on attempt {attempt + 1}"
                    )
                
                return result
                
            except retryable_exceptions as e:
                last_exception = e
                
                if attempt < self.max_retries:
                    delay = self.calculate_delay(attempt)
                    logger.warning(
                        f"Function {func.__name__} failed on attempt {attempt + 1}, "
                        f"retrying in {delay:.2f}s: {e}"
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"Function {func.__name__} failed after {self.max_retries + 1} attempts: {e}"
                    )
            
            except Exception as e:
                # Non-retryable exception
                logger.error(
                    f"Function {func.__name__} failed with non-retryable error: {e}"
                )
                raise
        
        # All retries exhausted
        raise last_exception


def with_retry(
    max_retries: int = 3,
    base_delay: float = 2.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    retryable_exceptions: Optional[Tuple[Type[Exception], ...]] = None
):
    """
    Decorator to add retry logic to async functions
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Base for exponential backoff calculation
        retryable_exceptions: Tuple of exception types to retry on
    
    Example:
        @with_retry(max_retries=3, base_delay=2.0)
        async def fetch_product_info(url: str):
            # Function implementation
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            strategy = RetryStrategy(
                max_retries=max_retries,
                base_delay=base_delay,
                max_delay=max_delay,
                exponential_base=exponential_base
            )
            
            return await strategy.execute_with_retry(
                func,
                *args,
                retryable_exceptions=retryable_exceptions,
                **kwargs
            )
        
        return wrapper
    
    return decorator


class CircuitBreaker:
    """
    Circuit breaker pattern to prevent cascading failures
    
    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Too many failures, requests fail immediately
    - HALF_OPEN: Testing if service recovered
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: Type[Exception] = Exception
    ):
        """
        Initialize circuit breaker
        
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
            expected_exception: Exception type to track
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = "CLOSED"
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function through circuit breaker
        
        Args:
            func: The async function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
        
        Returns:
            Result of the function
        
        Raises:
            Exception if circuit is open or function fails
        """
        if self.state == "OPEN":
            # Check if recovery timeout has passed
            if self.last_failure_time:
                elapsed = asyncio.get_event_loop().time() - self.last_failure_time
                if elapsed >= self.recovery_timeout:
                    logger.info("Circuit breaker entering HALF_OPEN state")
                    self.state = "HALF_OPEN"
                else:
                    raise Exception(
                        f"Circuit breaker is OPEN. "
                        f"Retry in {self.recovery_timeout - elapsed:.1f}s"
                    )
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = await func(*args, **kwargs)
            
            # Success - reset failure count
            if self.state == "HALF_OPEN":
                logger.info("Circuit breaker closing after successful recovery")
                self.state = "CLOSED"
            
            self.failure_count = 0
            return result
            
        except self.expected_exception as e:
            self.failure_count += 1
            self.last_failure_time = asyncio.get_event_loop().time()
            
            if self.failure_count >= self.failure_threshold:
                logger.error(
                    f"Circuit breaker opening after {self.failure_count} failures"
                )
                self.state = "OPEN"
            
            raise


def with_circuit_breaker(
    failure_threshold: int = 5,
    recovery_timeout: float = 60.0,
    expected_exception: Type[Exception] = Exception
):
    """
    Decorator to add circuit breaker pattern to async functions
    
    Args:
        failure_threshold: Number of failures before opening circuit
        recovery_timeout: Seconds to wait before attempting recovery
        expected_exception: Exception type to track
    
    Example:
        @with_circuit_breaker(failure_threshold=5, recovery_timeout=60.0)
        async def call_external_api():
            # Function implementation
            pass
    """
    circuit_breaker = CircuitBreaker(
        failure_threshold=failure_threshold,
        recovery_timeout=recovery_timeout,
        expected_exception=expected_exception
    )
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            return await circuit_breaker.call(func, *args, **kwargs)
        
        return wrapper
    
    return decorator
