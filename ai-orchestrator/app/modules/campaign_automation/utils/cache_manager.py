"""
Cache manager for Campaign Automation module.

Provides caching functionality for campaign status data to reduce API calls
and improve performance.

Requirements: 8.4
"""

import json
from typing import Any, Callable
import structlog
from redis.asyncio import Redis

logger = structlog.get_logger(__name__)


class CacheManager:
    """Manages caching of campaign data with Redis
    
    Provides methods to cache and retrieve campaign status data with automatic
    expiration and fallback logic.
    
    Requirements: 8.4
    """
    
    def __init__(self, redis_client: Redis):
        """Initialize cache manager
        
        Args:
            redis_client: Redis client instance
        """
        self.redis = redis_client
        self.default_ttl = 300  # 5 minutes in seconds
        
        logger.info(
            "cache_manager_initialized",
            default_ttl=self.default_ttl,
        )
    
    async def get_or_fetch(
        self,
        key: str,
        fetch_func: Callable,
        ttl: int | None = None,
    ) -> Any:
        """Get cached data or fetch from source
        
        Attempts to retrieve data from cache. If not found or expired,
        executes the fetch function and caches the result.
        
        Args:
            key: Cache key
            fetch_func: Async function to fetch data if cache miss
            ttl: Optional TTL in seconds (defaults to 5 minutes)
            
        Returns:
            Cached or freshly fetched data
            
        Requirements: 8.4
        """
        cache_ttl = ttl or self.default_ttl
        
        log = logger.bind(
            cache_key=key,
            ttl=cache_ttl,
        )
        
        try:
            # Try to get from cache
            cached_value = await self.redis.get(key)
            
            if cached_value:
                log.info("cache_hit")
                try:
                    return json.loads(cached_value)
                except json.JSONDecodeError as e:
                    log.warning("cache_parse_error", error=str(e))
                    # Invalidate corrupted cache entry
                    await self.redis.delete(key)
            else:
                log.info("cache_miss")
            
        except Exception as e:
            log.warning("cache_get_error", error=str(e))
            # Continue to fetch from source on cache errors
        
        # Cache miss or error - fetch from source
        log.info("fetching_from_source")
        try:
            data = await fetch_func()
            
            # Cache the result
            try:
                json_data = json.dumps(data, ensure_ascii=False)
                await self.redis.setex(key, cache_ttl, json_data)
                log.info("cache_set_success")
            except Exception as e:
                log.warning("cache_set_error", error=str(e))
                # Continue even if caching fails
            
            return data
            
        except Exception as e:
            log.error("fetch_from_source_failed", error=str(e))
            # Try to return stale cache as fallback
            try:
                stale_value = await self.redis.get(key)
                if stale_value:
                    log.warning("returning_stale_cache")
                    return json.loads(stale_value)
            except Exception:
                pass
            
            # Re-raise the original error if no fallback available
            raise
    
    async def invalidate(self, pattern: str) -> int:
        """Invalidate cached entries matching pattern
        
        Removes all cache entries matching the specified pattern.
        Supports Redis glob-style patterns (*, ?, []).
        
        Args:
            pattern: Cache key pattern (e.g., "campaign:*", "campaign:123:*")
            
        Returns:
            Number of cache entries deleted
            
        Requirements: 8.4
        """
        log = logger.bind(pattern=pattern)
        log.info("cache_invalidation_start")
        
        try:
            # Find matching keys
            keys = []
            async for key in self.redis.scan_iter(match=pattern):
                keys.append(key)
            
            # Delete keys
            deleted_count = 0
            if keys:
                deleted_count = await self.redis.delete(*keys)
            
            log.info(
                "cache_invalidation_complete",
                deleted_count=deleted_count,
            )
            
            return deleted_count
            
        except Exception as e:
            log.error("cache_invalidation_error", error=str(e))
            return 0
    
    async def get_campaign_status(
        self,
        campaign_id: str,
        platform: str,
        fetch_func: Callable,
    ) -> dict:
        """Get campaign status with caching
        
        Specialized method for caching campaign status data.
        Uses a 5-minute TTL and provides fallback to stale cache on errors.
        
        Args:
            campaign_id: Campaign ID
            platform: Platform name (meta, tiktok, google)
            fetch_func: Async function to fetch status from platform API
            
        Returns:
            Campaign status dict
            
        Requirements: 8.4
        """
        cache_key = self._build_campaign_cache_key(campaign_id, platform)
        return await self.get_or_fetch(cache_key, fetch_func)
    
    async def invalidate_campaign(
        self,
        campaign_id: str,
        platform: str | None = None,
    ) -> int:
        """Invalidate campaign cache
        
        Removes cached campaign data. If platform is None, invalidates
        all cache entries for the campaign across all platforms.
        
        Args:
            campaign_id: Campaign ID
            platform: Optional platform filter
            
        Returns:
            Number of cache entries deleted
            
        Requirements: 8.4
        """
        if platform:
            pattern = self._build_campaign_cache_key(campaign_id, platform)
        else:
            pattern = f"campaign:{campaign_id}:*"
        
        return await self.invalidate(pattern)
    
    def _build_campaign_cache_key(
        self,
        campaign_id: str,
        platform: str,
    ) -> str:
        """Build cache key for campaign status
        
        Args:
            campaign_id: Campaign ID
            platform: Platform name
            
        Returns:
            Cache key string
        """
        return f"campaign:{campaign_id}:{platform}:status"
