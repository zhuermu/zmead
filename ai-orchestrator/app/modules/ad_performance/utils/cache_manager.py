"""
Cache manager for Ad Performance module.

Provides caching functionality for metrics data to reduce API calls
and improve performance.

Requirements: Performance requirements
"""

import json
from typing import Any
import structlog
from redis.asyncio import Redis

logger = structlog.get_logger(__name__)


class CacheManager:
    """Manages caching of metrics data with Redis
    
    Provides methods to cache and retrieve metrics data with automatic
    expiration and invalidation logic.
    
    Requirements: Performance requirements
    """
    
    def __init__(self, redis_client: Redis):
        """Initialize cache manager
        
        Args:
            redis_client: Redis client instance
        """
        self.redis = redis_client
        self.cache_ttl = 300  # 5 minutes in seconds
        
        logger.info(
            "cache_manager_initialized",
            cache_ttl=self.cache_ttl,
        )
    
    async def get_cached_metrics(
        self,
        user_id: str,
        date: str,
        platform: str | None = None,
    ) -> dict | None:
        """Get cached metrics data
        
        Retrieves metrics from cache if available and not expired.
        
        Args:
            user_id: User ID
            date: Date in ISO format (YYYY-MM-DD)
            platform: Optional platform filter (meta, tiktok, google)
            
        Returns:
            Cached metrics dict if found, None otherwise
            
        Requirements: Performance requirements
        """
        cache_key = self._build_cache_key(user_id, date, platform)
        
        log = logger.bind(
            user_id=user_id,
            date=date,
            platform=platform,
            cache_key=cache_key,
        )
        
        try:
            cached_value = await self.redis.get(cache_key)
            
            if cached_value:
                log.info("cache_hit")
                metrics = json.loads(cached_value)
                return metrics
            else:
                log.info("cache_miss")
                return None
                
        except json.JSONDecodeError as e:
            log.warning("cache_parse_error", error=str(e))
            # Invalidate corrupted cache entry
            await self.redis.delete(cache_key)
            return None
            
        except Exception as e:
            log.error("cache_get_error", error=str(e))
            # Return None on cache errors to allow fallback to source
            return None
    
    async def cache_metrics(
        self,
        user_id: str,
        date: str,
        platform: str | None,
        data: dict,
    ) -> bool:
        """Cache metrics data
        
        Stores metrics in cache with TTL expiration.
        
        Args:
            user_id: User ID
            date: Date in ISO format (YYYY-MM-DD)
            platform: Optional platform filter (meta, tiktok, google)
            data: Metrics data to cache
            
        Returns:
            True if successful, False otherwise
            
        Requirements: Performance requirements
        """
        cache_key = self._build_cache_key(user_id, date, platform)
        
        log = logger.bind(
            user_id=user_id,
            date=date,
            platform=platform,
            cache_key=cache_key,
            ttl=self.cache_ttl,
        )
        
        try:
            # Serialize data to JSON
            json_data = json.dumps(data, ensure_ascii=False)
            
            # Store in Redis with TTL
            result = await self.redis.setex(
                cache_key,
                self.cache_ttl,
                json_data,
            )
            
            if result:
                log.info("cache_set_success")
                return True
            else:
                log.warning("cache_set_failed")
                return False
                
        except (TypeError, ValueError) as e:
            log.error("cache_serialization_error", error=str(e))
            return False
            
        except Exception as e:
            log.error("cache_set_error", error=str(e))
            return False
    
    async def invalidate_cache(
        self,
        user_id: str,
        date: str | None = None,
        platform: str | None = None,
    ) -> int:
        """Invalidate cached metrics
        
        Removes cached entries matching the specified criteria.
        If date is None, invalidates all cache entries for the user.
        
        Args:
            user_id: User ID
            date: Optional date filter (YYYY-MM-DD)
            platform: Optional platform filter (meta, tiktok, google)
            
        Returns:
            Number of cache entries deleted
            
        Requirements: Performance requirements
        """
        log = logger.bind(
            user_id=user_id,
            date=date,
            platform=platform,
        )
        log.info("cache_invalidation_start")
        
        try:
            if date is None:
                # Invalidate all cache entries for user
                pattern = f"metrics:{user_id}:*"
            else:
                # Invalidate specific date/platform
                cache_key = self._build_cache_key(user_id, date, platform)
                pattern = cache_key
            
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
                pattern=pattern,
            )
            
            return deleted_count
            
        except Exception as e:
            log.error("cache_invalidation_error", error=str(e))
            return 0
    
    def _build_cache_key(
        self,
        user_id: str,
        date: str,
        platform: str | None = None,
    ) -> str:
        """Build cache key from parameters
        
        Args:
            user_id: User ID
            date: Date in ISO format
            platform: Optional platform
            
        Returns:
            Cache key string
        """
        if platform:
            return f"metrics:{user_id}:{platform}:{date}"
        else:
            return f"metrics:{user_id}:all:{date}"
