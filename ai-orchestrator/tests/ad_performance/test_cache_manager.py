"""
Unit tests for CacheManager.

Tests the caching functionality including get, set, and invalidation.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
import json

from app.modules.ad_performance.utils.cache_manager import CacheManager


@pytest.fixture
def mock_redis():
    """Create a mock Redis client"""
    redis = AsyncMock()
    return redis


@pytest.fixture
def cache_manager(mock_redis):
    """Create a CacheManager instance with mock Redis"""
    return CacheManager(redis_client=mock_redis)


@pytest.mark.asyncio
async def test_cache_manager_initialization(cache_manager):
    """Test CacheManager initializes with correct TTL"""
    assert cache_manager.cache_ttl == 300  # 5 minutes
    assert cache_manager.redis is not None


@pytest.mark.asyncio
async def test_get_cached_metrics_hit(cache_manager, mock_redis):
    """Test getting cached metrics when cache hit"""
    # Arrange
    user_id = "user123"
    date = "2024-11-28"
    platform = "meta"
    
    cached_data = {
        "total_spend": 100.0,
        "total_revenue": 300.0,
        "avg_roas": 3.0,
    }
    
    mock_redis.get.return_value = json.dumps(cached_data)
    
    # Act
    result = await cache_manager.get_cached_metrics(user_id, date, platform)
    
    # Assert
    assert result == cached_data
    mock_redis.get.assert_called_once_with(f"metrics:{user_id}:{platform}:{date}")


@pytest.mark.asyncio
async def test_get_cached_metrics_miss(cache_manager, mock_redis):
    """Test getting cached metrics when cache miss"""
    # Arrange
    user_id = "user123"
    date = "2024-11-28"
    platform = "meta"
    
    mock_redis.get.return_value = None
    
    # Act
    result = await cache_manager.get_cached_metrics(user_id, date, platform)
    
    # Assert
    assert result is None
    mock_redis.get.assert_called_once()


@pytest.mark.asyncio
async def test_get_cached_metrics_parse_error(cache_manager, mock_redis):
    """Test getting cached metrics with corrupted data"""
    # Arrange
    user_id = "user123"
    date = "2024-11-28"
    platform = "meta"
    
    mock_redis.get.return_value = "invalid json"
    
    # Act
    result = await cache_manager.get_cached_metrics(user_id, date, platform)
    
    # Assert
    assert result is None
    # Should delete corrupted cache entry
    mock_redis.delete.assert_called_once()


@pytest.mark.asyncio
async def test_cache_metrics_success(cache_manager, mock_redis):
    """Test caching metrics successfully"""
    # Arrange
    user_id = "user123"
    date = "2024-11-28"
    platform = "meta"
    data = {
        "total_spend": 100.0,
        "total_revenue": 300.0,
        "avg_roas": 3.0,
    }
    
    mock_redis.setex.return_value = True
    
    # Act
    result = await cache_manager.cache_metrics(user_id, date, platform, data)
    
    # Assert
    assert result is True
    mock_redis.setex.assert_called_once()
    
    # Verify the call arguments
    call_args = mock_redis.setex.call_args
    assert call_args[0][0] == f"metrics:{user_id}:{platform}:{date}"
    assert call_args[0][1] == 300  # TTL
    assert json.loads(call_args[0][2]) == data


@pytest.mark.asyncio
async def test_cache_metrics_no_platform(cache_manager, mock_redis):
    """Test caching metrics without platform filter"""
    # Arrange
    user_id = "user123"
    date = "2024-11-28"
    data = {"total_spend": 100.0}
    
    mock_redis.setex.return_value = True
    
    # Act
    result = await cache_manager.cache_metrics(user_id, date, None, data)
    
    # Assert
    assert result is True
    call_args = mock_redis.setex.call_args
    assert call_args[0][0] == f"metrics:{user_id}:all:{date}"


@pytest.mark.asyncio
async def test_cache_metrics_serialization_error(cache_manager, mock_redis):
    """Test caching metrics with non-serializable data"""
    # Arrange
    user_id = "user123"
    date = "2024-11-28"
    platform = "meta"
    
    # Create non-serializable data
    class NonSerializable:
        pass
    
    data = {"obj": NonSerializable()}
    
    # Act
    result = await cache_manager.cache_metrics(user_id, date, platform, data)
    
    # Assert
    assert result is False
    mock_redis.setex.assert_not_called()


@pytest.mark.asyncio
async def test_invalidate_cache_specific_date(cache_manager, mock_redis):
    """Test invalidating cache for specific date"""
    # Arrange
    user_id = "user123"
    date = "2024-11-28"
    platform = "meta"
    
    # Mock scan_iter to return matching keys
    async def mock_scan_iter(match):
        keys = [f"metrics:{user_id}:{platform}:{date}"]
        for key in keys:
            yield key
    
    mock_redis.scan_iter = mock_scan_iter
    mock_redis.delete.return_value = 1
    
    # Act
    deleted_count = await cache_manager.invalidate_cache(user_id, date, platform)
    
    # Assert
    assert deleted_count == 1
    mock_redis.delete.assert_called_once()


@pytest.mark.asyncio
async def test_invalidate_cache_all_user_data(cache_manager, mock_redis):
    """Test invalidating all cache entries for a user"""
    # Arrange
    user_id = "user123"
    
    # Mock scan_iter to return multiple keys
    async def mock_scan_iter(match):
        keys = [
            f"metrics:{user_id}:meta:2024-11-28",
            f"metrics:{user_id}:tiktok:2024-11-28",
            f"metrics:{user_id}:all:2024-11-27",
        ]
        for key in keys:
            yield key
    
    mock_redis.scan_iter = mock_scan_iter
    mock_redis.delete.return_value = 3
    
    # Act
    deleted_count = await cache_manager.invalidate_cache(user_id, date=None)
    
    # Assert
    assert deleted_count == 3
    mock_redis.delete.assert_called_once()


@pytest.mark.asyncio
async def test_invalidate_cache_no_matches(cache_manager, mock_redis):
    """Test invalidating cache when no matching keys exist"""
    # Arrange
    user_id = "user123"
    date = "2024-11-28"
    
    # Mock scan_iter to return no keys
    async def mock_scan_iter(match):
        return
        yield  # Make it a generator
    
    mock_redis.scan_iter = mock_scan_iter
    
    # Act
    deleted_count = await cache_manager.invalidate_cache(user_id, date)
    
    # Assert
    assert deleted_count == 0
    mock_redis.delete.assert_not_called()


@pytest.mark.asyncio
async def test_build_cache_key_with_platform(cache_manager):
    """Test building cache key with platform"""
    # Act
    key = cache_manager._build_cache_key("user123", "2024-11-28", "meta")
    
    # Assert
    assert key == "metrics:user123:meta:2024-11-28"


@pytest.mark.asyncio
async def test_build_cache_key_without_platform(cache_manager):
    """Test building cache key without platform"""
    # Act
    key = cache_manager._build_cache_key("user123", "2024-11-28", None)
    
    # Assert
    assert key == "metrics:user123:all:2024-11-28"
