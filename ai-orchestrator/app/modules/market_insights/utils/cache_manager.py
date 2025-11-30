"""
Cache manager for Market Insights module.

Provides caching functionality for market data to reduce API calls,
improve performance, and support degradation scenarios.

Requirements: 7.1, 7.2, 7.3, 7.4, 7.5
"""

import json
import time
from typing import Any, Callable

import structlog
from redis.asyncio import Redis

logger = structlog.get_logger(__name__)


class CacheManager:
    """Manages caching of market insights data with Redis.
    
    Provides methods to cache and retrieve market data with automatic
    expiration, stale cache fallback, and degradation support.
    
    TTL Configuration:
    - Trending creatives: 12 hours (43200 seconds)
    - Market trends: 24 hours (86400 seconds)
    - Competitor analysis: 1 hour (3600 seconds)
    
    Requirements: 7.1, 7.2, 7.3, 7.4, 7.5
    """
    
    # TTL configuration in seconds
    TTL_TRENDING_CREATIVES = 43200  # 12 hours
    TTL_MARKET_TRENDS = 86400  # 24 hours
    TTL_COMPETITOR_ANALYSIS = 3600  # 1 hour
    TTL_STALE_CACHE = 604800  # 7 days for stale cache fallback
    
    # Cache type to TTL mapping
    TTL_CONFIG = {
        "trending_creatives": TTL_TRENDING_CREATIVES,
        "market_trends": TTL_MARKET_TRENDS,
        "competitor_analysis": TTL_COMPETITOR_ANALYSIS,
    }
    
    def __init__(self, redis_client: Redis):
        """Initialize cache manager.
        
        Args:
            redis_client: Redis client instance
        """
        self.redis = redis_client
        
        logger.info(
            "market_insights_cache_manager_initialized",
            ttl_trending_creatives=self.TTL_TRENDING_CREATIVES,
            ttl_market_trends=self.TTL_MARKET_TRENDS,
            ttl_competitor_analysis=self.TTL_COMPETITOR_ANALYSIS,
        )
    
    async def get(self, cache_type: str, key: str) -> dict | None:
        """Get cached data.
        
        Retrieves data from cache if it exists and hasn't expired.
        
        Args:
            cache_type: Type of cache (trending_creatives, market_trends, etc.)
            key: Cache key identifier
            
        Returns:
            Cached data dict or None if not found/expired
            
        Requirements: 7.3
        """
        cache_key = self._build_cache_key(cache_type, key)
        log = logger.bind(cache_type=cache_type, cache_key=cache_key)
        
        try:
            cached_value = await self.redis.get(cache_key)
            
            if cached_value:
                log.info("cache_hit")
                try:
                    return json.loads(cached_value)
                except json.JSONDecodeError as e:
                    log.warning("cache_parse_error", error=str(e))
                    await self.redis.delete(cache_key)
                    return None
            
            log.debug("cache_miss")
            return None
            
        except Exception as e:
            log.warning("cache_get_error", error=str(e))
            return None
    
    async def set(
        self,
        cache_type: str,
        key: str,
        data: dict,
        ttl: int | None = None,
    ) -> bool:
        """Set cached data.
        
        Stores data in cache with appropriate TTL based on cache type.
        
        Args:
            cache_type: Type of cache (trending_creatives, market_trends, etc.)
            key: Cache key identifier
            data: Data to cache
            ttl: Optional custom TTL in seconds (uses default for cache_type if not provided)
            
        Returns:
            True if cache was set successfully, False otherwise
            
        Requirements: 7.1, 7.2, 7.4
        """
        cache_key = self._build_cache_key(cache_type, key)
        cache_ttl = ttl or self.TTL_CONFIG.get(cache_type, 3600)
        
        log = logger.bind(
            cache_type=cache_type,
            cache_key=cache_key,
            ttl=cache_ttl,
        )
        
        try:
            json_data = json.dumps(data, ensure_ascii=False)
            await self.redis.setex(cache_key, cache_ttl, json_data)
            log.info("cache_set_success")
            return True
            
        except Exception as e:
            log.warning("cache_set_error", error=str(e))
            return False

    async def get_stale_cache(
        self,
        cache_type: str,
        key: str,
        max_age: int | None = None,
    ) -> dict | None:
        """Get stale cache data for degradation scenarios.
        
        Retrieves cached data even if it's past its normal TTL,
        useful for fallback when APIs are unavailable.
        
        Args:
            cache_type: Type of cache
            key: Cache key identifier
            max_age: Maximum age in seconds to accept (default: 7 days)
            
        Returns:
            Stale cached data or None if not available or too old
            
        Requirements: 7.5
        """
        stale_key = self._build_stale_cache_key(cache_type, key)
        max_stale_age = max_age or self.TTL_STALE_CACHE
        
        log = logger.bind(
            cache_type=cache_type,
            stale_key=stale_key,
            max_age=max_stale_age,
        )
        
        try:
            cached_value = await self.redis.get(stale_key)
            
            if cached_value:
                try:
                    stale_data = json.loads(cached_value)
                    cached_at = stale_data.get("cached_at", 0)
                    age = time.time() - cached_at
                    
                    if age < max_stale_age:
                        log.info(
                            "stale_cache_hit",
                            age_seconds=int(age),
                        )
                        return stale_data.get("data")
                    else:
                        log.debug(
                            "stale_cache_too_old",
                            age_seconds=int(age),
                        )
                        return None
                        
                except json.JSONDecodeError as e:
                    log.warning("stale_cache_parse_error", error=str(e))
                    return None
            
            log.debug("stale_cache_miss")
            return None
            
        except Exception as e:
            log.warning("stale_cache_get_error", error=str(e))
            return None
    
    async def set_with_stale(
        self,
        cache_type: str,
        key: str,
        data: dict,
        ttl: int | None = None,
    ) -> bool:
        """Set cache with stale backup for degradation.
        
        Stores data in both normal cache and stale cache.
        The stale cache is kept longer for fallback scenarios.
        
        Args:
            cache_type: Type of cache
            key: Cache key identifier
            data: Data to cache
            ttl: Optional custom TTL for normal cache
            
        Returns:
            True if both caches were set successfully
            
        Requirements: 7.1, 7.2, 7.4, 7.5
        """
        log = logger.bind(cache_type=cache_type, key=key)
        
        # Set normal cache
        normal_success = await self.set(cache_type, key, data, ttl)
        
        # Set stale cache with timestamp
        stale_key = self._build_stale_cache_key(cache_type, key)
        stale_data = {
            "data": data,
            "cached_at": time.time(),
        }
        
        try:
            json_data = json.dumps(stale_data, ensure_ascii=False)
            await self.redis.setex(stale_key, self.TTL_STALE_CACHE, json_data)
            log.info("stale_cache_set_success")
            stale_success = True
        except Exception as e:
            log.warning("stale_cache_set_error", error=str(e))
            stale_success = False
        
        return normal_success and stale_success
    
    async def invalidate(self, cache_type: str, key: str) -> bool:
        """Invalidate cache entry.
        
        Removes both normal and stale cache entries.
        
        Args:
            cache_type: Type of cache
            key: Cache key identifier
            
        Returns:
            True if invalidation was successful
        """
        cache_key = self._build_cache_key(cache_type, key)
        stale_key = self._build_stale_cache_key(cache_type, key)
        
        log = logger.bind(cache_type=cache_type, key=key)
        
        try:
            await self.redis.delete(cache_key, stale_key)
            log.info("cache_invalidated")
            return True
        except Exception as e:
            log.warning("cache_invalidation_error", error=str(e))
            return False
    
    async def get_or_fetch(
        self,
        cache_type: str,
        key: str,
        fetch_func: Callable,
        ttl: int | None = None,
        use_stale_on_error: bool = True,
    ) -> dict:
        """Get cached data or fetch from source.
        
        Attempts to retrieve data from cache. If not found or expired,
        executes the fetch function and caches the result.
        Falls back to stale cache on fetch errors if enabled.
        
        Args:
            cache_type: Type of cache
            key: Cache key identifier
            fetch_func: Async function to fetch data if cache miss
            ttl: Optional custom TTL
            use_stale_on_error: Whether to use stale cache on fetch errors
            
        Returns:
            Cached or freshly fetched data
            
        Raises:
            Exception: If fetch fails and no stale cache available
            
        Requirements: 7.3, 7.4, 7.5
        """
        log = logger.bind(cache_type=cache_type, key=key)
        
        # Try normal cache first
        cached_data = await self.get(cache_type, key)
        if cached_data is not None:
            return cached_data
        
        # Cache miss - fetch from source
        log.info("fetching_from_source")
        try:
            data = await fetch_func()
            
            # Cache the result with stale backup
            await self.set_with_stale(cache_type, key, data, ttl)
            
            return data
            
        except Exception as e:
            log.error("fetch_from_source_failed", error=str(e))
            
            # Try stale cache as fallback
            if use_stale_on_error:
                stale_data = await self.get_stale_cache(cache_type, key)
                if stale_data is not None:
                    log.warning("returning_stale_cache_on_error")
                    return stale_data
            
            # Re-raise if no fallback available
            raise
    
    def _build_cache_key(self, cache_type: str, key: str) -> str:
        """Build cache key.
        
        Args:
            cache_type: Type of cache
            key: Key identifier
            
        Returns:
            Full cache key string
        """
        return f"market_insights:{cache_type}:{key}"
    
    def _build_stale_cache_key(self, cache_type: str, key: str) -> str:
        """Build stale cache key.
        
        Args:
            cache_type: Type of cache
            key: Key identifier
            
        Returns:
            Full stale cache key string
        """
        return f"market_insights:{cache_type}:stale:{key}"
    
    def get_ttl_for_type(self, cache_type: str) -> int:
        """Get TTL for a cache type.
        
        Args:
            cache_type: Type of cache
            
        Returns:
            TTL in seconds
        """
        return self.TTL_CONFIG.get(cache_type, 3600)
