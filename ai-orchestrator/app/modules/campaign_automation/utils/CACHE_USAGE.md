# Cache Manager Usage Guide

## Overview

The `CacheManager` provides Redis-based caching for campaign status data with automatic expiration and fallback mechanisms.

## Features

- **Automatic caching**: Cache data with configurable TTL (default 5 minutes)
- **Fallback to stale cache**: Returns stale cache data when source fetch fails
- **Pattern-based invalidation**: Invalidate multiple cache entries using glob patterns
- **Specialized campaign methods**: Convenient methods for campaign status caching

## Basic Usage

### Initialize Cache Manager

```python
from app.core.redis_client import get_redis
from app.modules.campaign_automation.utils import CacheManager

# Get Redis client
redis_client = await get_redis()

# Create cache manager
cache_manager = CacheManager(redis_client)
```

### Get or Fetch Pattern

The most common pattern - try cache first, fetch from source on miss:

```python
async def get_campaign_data(campaign_id: str):
    """Fetch campaign data from platform API"""
    # ... API call logic
    return campaign_data

# Use cache manager
cache_key = f"campaign:{campaign_id}:status"
data = await cache_manager.get_or_fetch(
    key=cache_key,
    fetch_func=lambda: get_campaign_data(campaign_id),
    ttl=300  # Optional: override default TTL
)
```

### Campaign-Specific Methods

For campaign status caching, use the specialized method:

```python
async def fetch_from_platform():
    """Fetch campaign status from Meta/TikTok/Google API"""
    return await platform_adapter.get_campaign_status(campaign_id)

# Cache campaign status
status = await cache_manager.get_campaign_status(
    campaign_id="campaign_123",
    platform="meta",
    fetch_func=fetch_from_platform
)
```

### Cache Invalidation

Invalidate cache when data changes:

```python
# Invalidate specific campaign on specific platform
deleted = await cache_manager.invalidate_campaign(
    campaign_id="campaign_123",
    platform="meta"
)

# Invalidate campaign across all platforms
deleted = await cache_manager.invalidate_campaign(
    campaign_id="campaign_123"
)

# Invalidate using pattern
deleted = await cache_manager.invalidate("campaign:*")
```

## Error Handling

The cache manager handles errors gracefully:

1. **Cache read errors**: Falls back to fetching from source
2. **Cache write errors**: Returns data even if caching fails
3. **Source fetch errors**: Returns stale cache if available, otherwise re-raises error

```python
try:
    data = await cache_manager.get_or_fetch(
        key="campaign:123:status",
        fetch_func=fetch_from_api
    )
except Exception as e:
    # Only raised if both cache and source fail
    logger.error("Failed to get data", error=str(e))
```

## Cache Key Patterns

Standard cache key patterns used in Campaign Automation:

- Campaign status: `campaign:{campaign_id}:{platform}:status`
- Campaign metrics: `campaign:{campaign_id}:{platform}:metrics`
- Adset status: `adset:{adset_id}:{platform}:status`

## TTL Configuration

Default TTL is 5 minutes (300 seconds). Override per-call:

```python
# Short TTL for frequently changing data
data = await cache_manager.get_or_fetch(
    key="campaign:123:status",
    fetch_func=fetch_func,
    ttl=60  # 1 minute
)

# Long TTL for stable data
data = await cache_manager.get_or_fetch(
    key="campaign:123:config",
    fetch_func=fetch_func,
    ttl=3600  # 1 hour
)
```

## Integration Example

Complete example in Campaign Manager:

```python
class CampaignManager:
    def __init__(self, redis_client):
        self.cache_manager = CacheManager(redis_client)
        self.platform_adapter = MetaAdapter()
    
    async def get_campaign_status(
        self,
        campaign_id: str,
        platform: str,
        use_cache: bool = True
    ) -> dict:
        """Get campaign status with optional caching"""
        
        if not use_cache:
            # Bypass cache
            return await self.platform_adapter.get_campaign_status(campaign_id)
        
        # Use cache
        return await self.cache_manager.get_campaign_status(
            campaign_id=campaign_id,
            platform=platform,
            fetch_func=lambda: self.platform_adapter.get_campaign_status(campaign_id)
        )
    
    async def update_campaign_budget(
        self,
        campaign_id: str,
        platform: str,
        new_budget: float
    ) -> dict:
        """Update campaign budget and invalidate cache"""
        
        # Update via API
        result = await self.platform_adapter.update_budget(campaign_id, new_budget)
        
        # Invalidate cache since data changed
        await self.cache_manager.invalidate_campaign(campaign_id, platform)
        
        return result
```

## Best Practices

1. **Always invalidate on updates**: Invalidate cache after any data modification
2. **Use appropriate TTLs**: Short TTL for dynamic data, longer for stable data
3. **Handle errors gracefully**: Don't let cache errors break your application
4. **Use pattern invalidation carefully**: Be specific to avoid invalidating too much
5. **Monitor cache hit rates**: Log cache hits/misses for optimization

## Requirements

This implementation satisfies requirement 8.4:
- ✅ Caches campaign status data with 5-minute TTL
- ✅ Provides fallback to stale cache on errors
- ✅ Supports pattern-based cache invalidation
- ✅ Integrates with Redis for distributed caching
