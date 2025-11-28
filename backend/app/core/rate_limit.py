"""Rate limiting middleware for API endpoints."""

import logging
import time
from typing import Callable

from fastapi import HTTPException, Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.redis import get_redis

logger = logging.getLogger(__name__)


class RateLimitExceeded(HTTPException):
    """Exception raised when rate limit is exceeded."""

    def __init__(self, retry_after: int) -> None:
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later.",
            headers={"Retry-After": str(retry_after)},
        )


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware using Redis.
    
    Implements per-user rate limiting with sliding window algorithm.
    """

    def __init__(
        self,
        app,
        requests_per_minute: int = 100,
        burst_multiplier: float = 1.5,
    ) -> None:
        """
        Initialize rate limit middleware.
        
        Args:
            app: FastAPI application
            requests_per_minute: Maximum requests per minute per user
            burst_multiplier: Allow burst traffic up to this multiplier
        """
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.burst_limit = int(requests_per_minute * burst_multiplier)
        self.window_size = 60  # 1 minute in seconds

    async def dispatch(
        self,
        request: Request,
        call_next: Callable,
    ) -> Response:
        """Process request with rate limiting."""
        # Skip rate limiting for health check, docs, and WebSocket endpoints
        if request.url.path in ["/health", "/docs", "/redoc", "/openapi.json"] or request.url.path.startswith("/ws/"):
            return await call_next(request)

        # Get user identifier from request
        user_id = self._get_user_id(request)
        
        if not user_id:
            # No user ID means unauthenticated request
            # Apply IP-based rate limiting for unauthenticated requests
            user_id = f"ip:{request.client.host}" if request.client else "unknown"

        # Check rate limit
        try:
            allowed, remaining, reset_time = await self._check_rate_limit(user_id)
            
            if not allowed:
                retry_after = int(reset_time - time.time())
                logger.warning(
                    f"Rate limit exceeded for {user_id}. "
                    f"Retry after {retry_after} seconds."
                )
                raise RateLimitExceeded(retry_after=max(1, retry_after))

            # Process request
            response = await call_next(request)

            # Add rate limit headers
            response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            response.headers["X-RateLimit-Reset"] = str(int(reset_time))

            return response

        except RateLimitExceeded:
            raise
        except Exception as e:
            logger.error(f"Rate limiting error: {e}")
            # On error, allow request to proceed (fail open)
            return await call_next(request)

    def _get_user_id(self, request: Request) -> str | None:
        """
        Extract user ID from request.
        
        Checks for user ID in request state (set by auth middleware).
        """
        # Check if user is authenticated (set by auth dependency)
        if hasattr(request.state, "user_id"):
            return f"user:{request.state.user_id}"
        
        # Check for user in request scope (alternative location)
        user = getattr(request.state, "user", None)
        if user and hasattr(user, "id"):
            return f"user:{user.id}"
        
        return None

    async def _check_rate_limit(
        self,
        user_id: str,
    ) -> tuple[bool, int, float]:
        """
        Check if request is within rate limit using sliding window.
        
        Returns:
            tuple of (allowed, remaining_requests, reset_timestamp)
        """
        redis = await get_redis()
        current_time = time.time()
        window_start = current_time - self.window_size

        # Redis key for this user's request timestamps
        key = f"rate_limit:{user_id}"

        try:
            # Remove old timestamps outside the window
            await redis.zremrangebyscore(key, 0, window_start)

            # Count requests in current window
            request_count = await redis.zcard(key)

            # Check if limit exceeded
            if request_count >= self.burst_limit:
                # Get oldest timestamp to calculate reset time
                oldest = await redis.zrange(key, 0, 0, withscores=True)
                if oldest:
                    reset_time = oldest[0][1] + self.window_size
                else:
                    reset_time = current_time + self.window_size
                
                remaining = 0
                allowed = False
            else:
                # Add current request timestamp
                await redis.zadd(key, {str(current_time): current_time})
                
                # Set expiry on key (cleanup)
                await redis.expire(key, self.window_size * 2)
                
                remaining = self.requests_per_minute - (request_count + 1)
                reset_time = current_time + self.window_size
                allowed = True

            return allowed, max(0, remaining), reset_time

        except Exception as e:
            logger.error(f"Redis error in rate limiting: {e}")
            # On Redis error, allow request (fail open)
            return True, self.requests_per_minute, current_time + self.window_size


class RateLimiter:
    """
    Decorator-based rate limiter for specific endpoints.
    
    Usage:
        @router.get("/expensive-operation")
        @rate_limit(requests_per_minute=10)
        async def expensive_operation():
            ...
    """

    def __init__(self, requests_per_minute: int = 60) -> None:
        """Initialize rate limiter with custom limit."""
        self.requests_per_minute = requests_per_minute
        self.window_size = 60

    async def __call__(
        self,
        request: Request,
        user_id: str | None = None,
    ) -> None:
        """Check rate limit for specific endpoint."""
        if not user_id:
            # Try to get user from request
            if hasattr(request.state, "user_id"):
                user_id = f"user:{request.state.user_id}"
            elif hasattr(request.state, "user") and hasattr(request.state.user, "id"):
                user_id = f"user:{request.state.user.id}"
            else:
                user_id = f"ip:{request.client.host}" if request.client else "unknown"

        redis = await get_redis()
        current_time = time.time()
        window_start = current_time - self.window_size

        # Endpoint-specific key
        endpoint = request.url.path
        key = f"rate_limit:{endpoint}:{user_id}"

        try:
            # Remove old timestamps
            await redis.zremrangebyscore(key, 0, window_start)

            # Count requests
            request_count = await redis.zcard(key)

            if request_count >= self.requests_per_minute:
                # Get reset time
                oldest = await redis.zrange(key, 0, 0, withscores=True)
                if oldest:
                    reset_time = oldest[0][1] + self.window_size
                else:
                    reset_time = current_time + self.window_size
                
                retry_after = int(reset_time - current_time)
                raise RateLimitExceeded(retry_after=max(1, retry_after))

            # Add current request
            await redis.zadd(key, {str(current_time): current_time})
            await redis.expire(key, self.window_size * 2)

        except RateLimitExceeded:
            raise
        except Exception as e:
            logger.error(f"Redis error in endpoint rate limiting: {e}")
            # On error, allow request


def rate_limit(requests_per_minute: int = 60):
    """
    Decorator for endpoint-specific rate limiting.
    
    Usage:
        @router.get("/expensive")
        @rate_limit(requests_per_minute=10)
        async def expensive_endpoint(request: Request):
            ...
    """
    limiter = RateLimiter(requests_per_minute=requests_per_minute)
    
    async def decorator(request: Request):
        await limiter(request)
    
    return decorator
