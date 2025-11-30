"""
Rate limiter for Market Insights module.

Provides rate limiting functionality for third-party API calls,
particularly for pytrends (Google Trends) which has strict rate limits.

Requirements: 6.2
"""

import asyncio
import time
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class RateLimiter:
    """Rate limiter with configurable requests per period.
    
    Implements a sliding window rate limiter to control API request rates.
    Default configuration for pytrends: 5 requests per minute.
    
    Requirements: 6.2
    """
    
    # Default configuration for pytrends
    DEFAULT_MAX_REQUESTS = 5
    DEFAULT_PERIOD = 60  # seconds (1 minute)
    
    def __init__(
        self,
        max_requests: int | None = None,
        period: int | None = None,
        name: str = "default",
    ):
        """Initialize rate limiter.
        
        Args:
            max_requests: Maximum requests allowed in the period (default: 5)
            period: Time period in seconds (default: 60)
            name: Name for logging purposes
        """
        self.max_requests = max_requests or self.DEFAULT_MAX_REQUESTS
        self.period = period or self.DEFAULT_PERIOD
        self.name = name
        self.requests: list[float] = []
        self._lock = asyncio.Lock()
        
        logger.info(
            "rate_limiter_initialized",
            name=self.name,
            max_requests=self.max_requests,
            period=self.period,
        )
    
    async def acquire(self) -> None:
        """Acquire permission to make a request.
        
        Blocks until a request slot is available within the rate limit.
        Uses a sliding window algorithm to track requests.
        
        Requirements: 6.2
        """
        async with self._lock:
            now = time.time()
            
            # Clean up expired request timestamps
            self.requests = [
                t for t in self.requests
                if now - t < self.period
            ]
            
            log = logger.bind(
                name=self.name,
                current_requests=len(self.requests),
                max_requests=self.max_requests,
            )
            
            if len(self.requests) >= self.max_requests:
                # Calculate wait time until oldest request expires
                oldest_request = self.requests[0]
                wait_time = self.period - (now - oldest_request)
                
                if wait_time > 0:
                    log.info(
                        "rate_limit_waiting",
                        wait_seconds=round(wait_time, 2),
                    )
                    await asyncio.sleep(wait_time)
                    
                    # Clean up again after waiting
                    now = time.time()
                    self.requests = [
                        t for t in self.requests
                        if now - t < self.period
                    ]
            
            # Record this request
            self.requests.append(time.time())
            log.debug(
                "rate_limit_acquired",
                requests_in_window=len(self.requests),
            )
    
    async def try_acquire(self) -> bool:
        """Try to acquire permission without blocking.
        
        Returns immediately with success/failure status.
        
        Returns:
            True if request is allowed, False if rate limited
        """
        async with self._lock:
            now = time.time()
            
            # Clean up expired request timestamps
            self.requests = [
                t for t in self.requests
                if now - t < self.period
            ]
            
            if len(self.requests) >= self.max_requests:
                logger.debug(
                    "rate_limit_exceeded",
                    name=self.name,
                    current_requests=len(self.requests),
                )
                return False
            
            # Record this request
            self.requests.append(now)
            return True
    
    def get_remaining_requests(self) -> int:
        """Get number of remaining requests in current window.
        
        Returns:
            Number of requests that can still be made
        """
        now = time.time()
        active_requests = len([
            t for t in self.requests
            if now - t < self.period
        ])
        return max(0, self.max_requests - active_requests)
    
    def get_reset_time(self) -> float:
        """Get time until rate limit resets.
        
        Returns:
            Seconds until a request slot becomes available
        """
        if not self.requests:
            return 0.0
        
        now = time.time()
        oldest_request = min(self.requests)
        reset_time = self.period - (now - oldest_request)
        return max(0.0, reset_time)
    
    def reset(self) -> None:
        """Reset the rate limiter.
        
        Clears all tracked requests. Use with caution.
        """
        self.requests = []
        logger.info("rate_limiter_reset", name=self.name)


class RateLimiterRegistry:
    """Registry for managing multiple rate limiters.
    
    Provides centralized access to rate limiters for different APIs.
    """
    
    _instance: "RateLimiterRegistry | None" = None
    _limiters: dict[str, RateLimiter] = {}
    
    def __new__(cls) -> "RateLimiterRegistry":
        """Singleton pattern for registry."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._limiters = {}
        return cls._instance
    
    @classmethod
    def get_limiter(
        cls,
        name: str,
        max_requests: int | None = None,
        period: int | None = None,
    ) -> RateLimiter:
        """Get or create a rate limiter.
        
        Args:
            name: Limiter name/identifier
            max_requests: Max requests (only used if creating new)
            period: Period in seconds (only used if creating new)
            
        Returns:
            RateLimiter instance
        """
        if name not in cls._limiters:
            cls._limiters[name] = RateLimiter(
                max_requests=max_requests,
                period=period,
                name=name,
            )
        return cls._limiters[name]
    
    @classmethod
    def get_pytrends_limiter(cls) -> RateLimiter:
        """Get rate limiter configured for pytrends.
        
        Configured for 5 requests per minute as per requirements.
        
        Returns:
            RateLimiter for pytrends API
            
        Requirements: 6.2
        """
        return cls.get_limiter(
            name="pytrends",
            max_requests=5,
            period=60,
        )
    
    @classmethod
    def get_tiktok_limiter(cls) -> RateLimiter:
        """Get rate limiter for TikTok Creative Center API.
        
        Returns:
            RateLimiter for TikTok API
        """
        return cls.get_limiter(
            name="tiktok",
            max_requests=30,  # More generous limit for official API
            period=60,
        )
    
    @classmethod
    def reset_all(cls) -> None:
        """Reset all rate limiters."""
        for limiter in cls._limiters.values():
            limiter.reset()
