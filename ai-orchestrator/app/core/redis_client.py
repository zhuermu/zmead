"""Redis client with connection pooling and retry logic."""

import asyncio
from typing import Any

import redis.asyncio as redis
from redis.asyncio.connection import ConnectionPool
from redis.exceptions import ConnectionError, TimeoutError

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Global connection pool
_pool: ConnectionPool | None = None
_client: redis.Redis | None = None


class RedisConnectionError(Exception):
    """Raised when Redis connection fails after retries."""

    pass


async def init_redis_pool() -> None:
    """Initialize the Redis connection pool.

    Should be called during application startup.
    """
    global _pool, _client

    settings = get_settings()

    logger.info(
        "Initializing Redis connection pool",
        redis_url=settings.redis_url.split("@")[-1],  # Hide password
        max_connections=settings.redis_max_connections,
    )

    _pool = ConnectionPool.from_url(
        settings.redis_url,
        max_connections=settings.redis_max_connections,
        socket_timeout=settings.redis_socket_timeout,
        socket_connect_timeout=settings.redis_socket_connect_timeout,
        decode_responses=True,
    )

    _client = redis.Redis(connection_pool=_pool)

    # Test connection
    try:
        await ping()
        logger.info("Redis connection pool initialized successfully")
    except RedisConnectionError as e:
        logger.error("Failed to connect to Redis during initialization", error=str(e))
        raise


async def close_redis_pool() -> None:
    """Close the Redis connection pool.

    Should be called during application shutdown.
    """
    global _pool, _client

    if _client:
        await _client.close()
        _client = None

    if _pool:
        await _pool.disconnect()
        _pool = None

    logger.info("Redis connection pool closed")


async def get_redis() -> redis.Redis:
    """Get Redis client instance for dependency injection.

    Returns:
        Redis client instance

    Raises:
        RedisConnectionError: If Redis is not initialized
    """
    if _client is None:
        raise RedisConnectionError("Redis client not initialized. Call init_redis_pool() first.")
    return _client


async def ping(max_retries: int = 3, retry_delay: float = 1.0) -> bool:
    """Health check - ping Redis server with retries.

    Args:
        max_retries: Maximum number of retry attempts
        retry_delay: Delay between retries in seconds

    Returns:
        True if ping successful

    Raises:
        RedisConnectionError: If ping fails after all retries
    """
    if _client is None:
        raise RedisConnectionError("Redis client not initialized")

    last_error: Exception | None = None

    for attempt in range(max_retries):
        try:
            result = await _client.ping()
            if result:
                return True
        except (ConnectionError, TimeoutError) as e:
            last_error = e
            if attempt < max_retries - 1:
                wait_time = retry_delay * (2**attempt)  # Exponential backoff
                logger.warning(
                    "Redis ping failed, retrying",
                    attempt=attempt + 1,
                    max_retries=max_retries,
                    wait_time=wait_time,
                    error=str(e),
                )
                await asyncio.sleep(wait_time)

    error_msg = f"Redis ping failed after {max_retries} attempts"
    logger.error(error_msg, last_error=str(last_error))
    raise RedisConnectionError(error_msg)


async def get_value(key: str) -> str | None:
    """Get a value from Redis.

    Args:
        key: Redis key

    Returns:
        Value if found, None otherwise
    """
    client = await get_redis()
    return await client.get(key)


async def set_value(
    key: str,
    value: str,
    expire: int | None = None,
) -> bool:
    """Set a value in Redis.

    Args:
        key: Redis key
        value: Value to store
        expire: Optional expiration time in seconds

    Returns:
        True if successful
    """
    client = await get_redis()
    return await client.set(key, value, ex=expire)


async def delete_key(key: str) -> int:
    """Delete a key from Redis.

    Args:
        key: Redis key to delete

    Returns:
        Number of keys deleted (0 or 1)
    """
    client = await get_redis()
    return await client.delete(key)


async def get_json(key: str) -> dict[str, Any] | None:
    """Get a JSON value from Redis.

    Args:
        key: Redis key

    Returns:
        Parsed JSON dict if found, None otherwise
    """
    import json

    value = await get_value(key)
    if value is None:
        return None

    try:
        return json.loads(value)
    except json.JSONDecodeError:
        logger.warning("Failed to parse JSON from Redis", key=key)
        return None


async def set_json(
    key: str,
    value: dict[str, Any],
    expire: int | None = None,
) -> bool:
    """Set a JSON value in Redis.

    Args:
        key: Redis key
        value: Dict to store as JSON
        expire: Optional expiration time in seconds

    Returns:
        True if successful
    """
    import json

    json_str = json.dumps(value, ensure_ascii=False)
    return await set_value(key, json_str, expire=expire)
