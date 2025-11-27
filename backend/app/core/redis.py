"""Redis connection and utilities."""

from typing import Any

import redis.asyncio as redis

from app.core.config import settings

# Create Redis connection pool
redis_pool = redis.ConnectionPool.from_url(
    settings.redis_url,
    decode_responses=True,
    max_connections=20,
)


async def get_redis() -> redis.Redis:  # type: ignore[type-arg]
    """Get Redis client instance."""
    return redis.Redis(connection_pool=redis_pool)


class RedisCache:
    """Redis cache utility class."""

    def __init__(self, client: redis.Redis) -> None:  # type: ignore[type-arg]
        self.client = client

    async def get(self, key: str) -> str | None:
        """Get value from cache."""
        return await self.client.get(key)

    async def set(
        self,
        key: str,
        value: str,
        expire: int | None = None,
    ) -> bool:
        """Set value in cache with optional expiration in seconds."""
        return await self.client.set(key, value, ex=expire)

    async def delete(self, key: str) -> int:
        """Delete key from cache."""
        return await self.client.delete(key)

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        return bool(await self.client.exists(key))

    async def incr(self, key: str) -> int:
        """Increment value by 1."""
        return await self.client.incr(key)

    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration on key."""
        return await self.client.expire(key, seconds)

    async def hset(self, name: str, mapping: dict[str, Any]) -> int:
        """Set hash fields."""
        return await self.client.hset(name, mapping=mapping)

    async def hget(self, name: str, key: str) -> str | None:
        """Get hash field value."""
        return await self.client.hget(name, key)

    async def hgetall(self, name: str) -> dict[str, str]:
        """Get all hash fields."""
        return await self.client.hgetall(name)


async def close_redis() -> None:
    """Close Redis connection pool."""
    await redis_pool.disconnect()
