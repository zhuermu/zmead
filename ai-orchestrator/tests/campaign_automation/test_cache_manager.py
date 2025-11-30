"""
Tests for Campaign Automation Cache Manager.

Requirements: 8.4
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from redis.asyncio import Redis

from app.modules.campaign_automation.utils.cache_manager import CacheManager


@pytest.fixture
def mock_redis():
    """Create a mock Redis client"""
    redis = AsyncMock(spec=Redis)
    # Make sure async methods return awaitable values
    redis.get = AsyncMock()
    redis.setex = AsyncMock()
    redis.delete = AsyncMock()
    redis.scan_iter = MagicMock()  # This returns an async generator
    return redis


@pytest.fixture
def cache_manager(mock_redis):
    """Create a CacheManager instance with mock Redis"""
    return CacheManager(mock_redis)


@pytest.mark.asyncio
async def test_cache_manager_initialization(mock_redis):
    """Test cache manager initializes with correct TTL"""
    manager = CacheManager(mock_redis)
    
    assert manager.redis == mock_redis
    assert manager.default_ttl == 300  # 5 minutes


@pytest.mark.asyncio
async def test_get_or_fetch_cache_hit(cache_manager, mock_redis):
    """Test get_or_fetch returns cached data on cache hit"""
    # Setup
    cache_key = "test:key"
    cached_data = {"status": "active", "name": "Test Campaign"}
    mock_redis.get.return_value = json.dumps(cached_data)
    
    fetch_func = AsyncMock()
    
    # Execute
    result = await cache_manager.get_or_fetch(cache_key, fetch_func)
    
    # Verify
    assert result == cached_data
    mock_redis.get.assert_called_once_with(cache_key)
    fetch_func.assert_not_called()  # Should not fetch on cache hit


@pytest.mark.asyncio
async def test_get_or_fetch_cache_miss(cache_manager, mock_redis):
    """Test get_or_fetch fetches and caches data on cache miss"""
    # Setup
    cache_key = "test:key"
    fresh_data = {"status": "active", "name": "Fresh Campaign"}
    mock_redis.get.return_value = None  # Cache miss
    mock_redis.setex.return_value = True
    
    fetch_func = AsyncMock(return_value=fresh_data)
    
    # Execute
    result = await cache_manager.get_or_fetch(cache_key, fetch_func)
    
    # Verify
    assert result == fresh_data
    mock_redis.get.assert_called_once_with(cache_key)
    fetch_func.assert_called_once()
    mock_redis.setex.assert_called_once_with(
        cache_key,
        300,  # default TTL
        json.dumps(fresh_data, ensure_ascii=False)
    )


@pytest.mark.asyncio
async def test_get_or_fetch_custom_ttl(cache_manager, mock_redis):
    """Test get_or_fetch uses custom TTL when provided"""
    # Setup
    cache_key = "test:key"
    fresh_data = {"status": "active"}
    custom_ttl = 600  # 10 minutes
    mock_redis.get.return_value = None
    mock_redis.setex.return_value = True
    
    fetch_func = AsyncMock(return_value=fresh_data)
    
    # Execute
    result = await cache_manager.get_or_fetch(cache_key, fetch_func, ttl=custom_ttl)
    
    # Verify
    assert result == fresh_data
    mock_redis.setex.assert_called_once_with(
        cache_key,
        custom_ttl,
        json.dumps(fresh_data, ensure_ascii=False)
    )


@pytest.mark.asyncio
async def test_get_or_fetch_corrupted_cache(cache_manager, mock_redis):
    """Test get_or_fetch handles corrupted cache data"""
    # Setup
    cache_key = "test:key"
    fresh_data = {"status": "active"}
    mock_redis.get.return_value = "invalid json {{"  # Corrupted data
    mock_redis.delete.return_value = 1
    mock_redis.setex.return_value = True
    
    fetch_func = AsyncMock(return_value=fresh_data)
    
    # Execute
    result = await cache_manager.get_or_fetch(cache_key, fetch_func)
    
    # Verify
    assert result == fresh_data
    mock_redis.delete.assert_called_once_with(cache_key)  # Should delete corrupted cache
    fetch_func.assert_called_once()


@pytest.mark.asyncio
async def test_get_or_fetch_cache_error_fallback(cache_manager, mock_redis):
    """Test get_or_fetch falls back to source on cache errors"""
    # Setup
    cache_key = "test:key"
    fresh_data = {"status": "active"}
    mock_redis.get.side_effect = Exception("Redis connection error")
    mock_redis.setex.return_value = True
    
    fetch_func = AsyncMock(return_value=fresh_data)
    
    # Execute
    result = await cache_manager.get_or_fetch(cache_key, fetch_func)
    
    # Verify
    assert result == fresh_data
    fetch_func.assert_called_once()


@pytest.mark.asyncio
async def test_get_or_fetch_stale_cache_fallback(cache_manager, mock_redis):
    """Test get_or_fetch returns stale cache when fetch fails"""
    # Setup
    cache_key = "test:key"
    stale_data = {"status": "active", "stale": True}
    
    # First call returns None (cache miss), second call returns stale data
    mock_redis.get.side_effect = [None, json.dumps(stale_data)]
    
    fetch_func = AsyncMock(side_effect=Exception("API error"))
    
    # Execute
    result = await cache_manager.get_or_fetch(cache_key, fetch_func)
    
    # Verify
    assert result == stale_data
    assert mock_redis.get.call_count == 2  # Once for normal check, once for fallback


@pytest.mark.asyncio
async def test_get_or_fetch_no_fallback_available(cache_manager, mock_redis):
    """Test get_or_fetch raises error when no fallback available"""
    # Setup
    cache_key = "test:key"
    mock_redis.get.return_value = None  # No cache available
    
    fetch_func = AsyncMock(side_effect=Exception("API error"))
    
    # Execute & Verify
    with pytest.raises(Exception, match="API error"):
        await cache_manager.get_or_fetch(cache_key, fetch_func)


@pytest.mark.asyncio
async def test_invalidate_pattern(cache_manager, mock_redis):
    """Test invalidate removes matching cache entries"""
    # Setup
    pattern = "campaign:*"
    matching_keys = ["campaign:123", "campaign:456", "campaign:789"]
    
    async def mock_scan_iter(match):
        for key in matching_keys:
            yield key
    
    mock_redis.scan_iter.return_value = mock_scan_iter(pattern)
    mock_redis.delete.return_value = len(matching_keys)
    
    # Execute
    deleted_count = await cache_manager.invalidate(pattern)
    
    # Verify
    assert deleted_count == 3
    mock_redis.scan_iter.assert_called_once_with(match=pattern)
    mock_redis.delete.assert_called_once_with(*matching_keys)


@pytest.mark.asyncio
async def test_invalidate_no_matches(cache_manager, mock_redis):
    """Test invalidate handles no matching keys"""
    # Setup
    pattern = "campaign:*"
    
    async def mock_scan_iter(match):
        return
        yield  # Empty generator
    
    mock_redis.scan_iter.return_value = mock_scan_iter(pattern)
    
    # Execute
    deleted_count = await cache_manager.invalidate(pattern)
    
    # Verify
    assert deleted_count == 0
    mock_redis.delete.assert_not_called()


@pytest.mark.asyncio
async def test_invalidate_error_handling(cache_manager, mock_redis):
    """Test invalidate handles errors gracefully"""
    # Setup
    pattern = "campaign:*"
    mock_redis.scan_iter.side_effect = Exception("Redis error")
    
    # Execute
    deleted_count = await cache_manager.invalidate(pattern)
    
    # Verify
    assert deleted_count == 0  # Should return 0 on error


@pytest.mark.asyncio
async def test_get_campaign_status(cache_manager, mock_redis):
    """Test get_campaign_status caches campaign data"""
    # Setup
    campaign_id = "campaign_123"
    platform = "meta"
    status_data = {
        "campaign_id": campaign_id,
        "status": "active",
        "spend": 100.0,
        "roas": 3.5
    }
    
    mock_redis.get.return_value = None
    mock_redis.setex.return_value = True
    
    fetch_func = AsyncMock(return_value=status_data)
    
    # Execute
    result = await cache_manager.get_campaign_status(campaign_id, platform, fetch_func)
    
    # Verify
    assert result == status_data
    expected_key = f"campaign:{campaign_id}:{platform}:status"
    mock_redis.get.assert_called_once_with(expected_key)
    mock_redis.setex.assert_called_once()


@pytest.mark.asyncio
async def test_invalidate_campaign_specific_platform(cache_manager, mock_redis):
    """Test invalidate_campaign for specific platform"""
    # Setup
    campaign_id = "campaign_123"
    platform = "meta"
    
    async def mock_scan_iter(match):
        yield f"campaign:{campaign_id}:{platform}:status"
    
    mock_redis.scan_iter.return_value = mock_scan_iter(None)
    mock_redis.delete.return_value = 1
    
    # Execute
    deleted_count = await cache_manager.invalidate_campaign(campaign_id, platform)
    
    # Verify
    assert deleted_count == 1
    expected_pattern = f"campaign:{campaign_id}:{platform}:status"
    mock_redis.scan_iter.assert_called_once_with(match=expected_pattern)


@pytest.mark.asyncio
async def test_invalidate_campaign_all_platforms(cache_manager, mock_redis):
    """Test invalidate_campaign for all platforms"""
    # Setup
    campaign_id = "campaign_123"
    matching_keys = [
        f"campaign:{campaign_id}:meta:status",
        f"campaign:{campaign_id}:tiktok:status",
        f"campaign:{campaign_id}:google:status"
    ]
    
    async def mock_scan_iter(match):
        for key in matching_keys:
            yield key
    
    mock_redis.scan_iter.return_value = mock_scan_iter(None)
    mock_redis.delete.return_value = len(matching_keys)
    
    # Execute
    deleted_count = await cache_manager.invalidate_campaign(campaign_id)
    
    # Verify
    assert deleted_count == 3
    expected_pattern = f"campaign:{campaign_id}:*"
    mock_redis.scan_iter.assert_called_once_with(match=expected_pattern)


@pytest.mark.asyncio
async def test_build_campaign_cache_key(cache_manager):
    """Test _build_campaign_cache_key generates correct keys"""
    campaign_id = "campaign_123"
    platform = "meta"
    
    key = cache_manager._build_campaign_cache_key(campaign_id, platform)
    
    assert key == f"campaign:{campaign_id}:{platform}:status"


@pytest.mark.asyncio
async def test_cache_set_error_continues(cache_manager, mock_redis):
    """Test that cache set errors don't prevent returning data"""
    # Setup
    cache_key = "test:key"
    fresh_data = {"status": "active"}
    mock_redis.get.return_value = None
    mock_redis.setex.side_effect = Exception("Redis write error")
    
    fetch_func = AsyncMock(return_value=fresh_data)
    
    # Execute - should not raise exception
    result = await cache_manager.get_or_fetch(cache_key, fetch_func)
    
    # Verify
    assert result == fresh_data  # Data should still be returned
    fetch_func.assert_called_once()
