"""
Tests for Market Insights data fetchers.

Tests TikTokFetcher and TrendsFetcher implementations.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.modules.market_insights.fetchers import TikTokFetcher, TrendsFetcher
from app.modules.market_insights.models import (
    TrendingCreative,
    TrendingCreativesResponse,
    KeywordTrend,
    MarketTrendsResponse,
)


class TestTikTokFetcher:
    """Tests for TikTokFetcher class."""
    
    def test_init(self):
        """Test TikTokFetcher initialization."""
        fetcher = TikTokFetcher(
            api_key="test_key",
            api_secret="test_secret",
        )
        assert fetcher.api_key == "test_key"
        assert fetcher.api_secret == "test_secret"
        assert fetcher.cache_manager is None
    
    def test_industry_map_exists(self):
        """Test industry mapping is defined."""
        fetcher = TikTokFetcher(
            api_key="test_key",
            api_secret="test_secret",
        )
        assert "fashion" in fetcher.INDUSTRY_MAP
        assert "electronics" in fetcher.INDUSTRY_MAP
        assert "beauty" in fetcher.INDUSTRY_MAP
    
    def test_time_range_map_exists(self):
        """Test time range mapping is defined."""
        fetcher = TikTokFetcher(
            api_key="test_key",
            api_secret="test_secret",
        )
        assert "1d" in fetcher.TIME_RANGE_MAP
        assert "7d" in fetcher.TIME_RANGE_MAP
        assert "30d" in fetcher.TIME_RANGE_MAP
    
    def test_transform_creatives(self):
        """Test creative transformation from API response."""
        fetcher = TikTokFetcher(
            api_key="test_key",
            api_secret="test_secret",
        )
        
        raw_data = [
            {
                "creative_id": "123",
                "title": "Test Creative",
                "thumbnail_url": "https://example.com/thumb.jpg",
                "play_count": 10000,
                "engagement_rate": 5.5,
            },
            {
                "id": "456",
                "name": "Another Creative",
                "cover_url": "https://example.com/cover.jpg",
                "views": 5000,
                "ctr": 3.2,
            },
        ]
        
        creatives = fetcher._transform_creatives(raw_data)
        
        assert len(creatives) == 2
        assert creatives[0].id == "123"
        assert creatives[0].title == "Test Creative"
        assert creatives[0].views == 10000
        assert creatives[0].platform == "tiktok"
        
        assert creatives[1].id == "456"
        assert creatives[1].title == "Another Creative"
        assert creatives[1].views == 5000
    
    def test_build_cache_key(self):
        """Test cache key generation."""
        fetcher = TikTokFetcher(
            api_key="test_key",
            api_secret="test_secret",
        )
        
        key1 = fetcher._build_cache_key("fashion", "US", "7d", 20)
        key2 = fetcher._build_cache_key("fashion", "US", "7d", 20)
        key3 = fetcher._build_cache_key("electronics", "US", "7d", 20)
        
        assert key1 == key2  # Same params = same key
        assert key1 != key3  # Different params = different key
        assert len(key1) == 16  # MD5 hash truncated to 16 chars


class TestTrendsFetcher:
    """Tests for TrendsFetcher class."""
    
    def test_init(self):
        """Test TrendsFetcher initialization."""
        fetcher = TrendsFetcher()
        assert fetcher.cache_manager is None
        assert fetcher._pytrends is None
    
    def test_time_range_map_exists(self):
        """Test time range mapping is defined."""
        fetcher = TrendsFetcher()
        assert "1d" in fetcher.TIME_RANGE_MAP
        assert "7d" in fetcher.TIME_RANGE_MAP
        assert "30d" in fetcher.TIME_RANGE_MAP
        assert "90d" in fetcher.TIME_RANGE_MAP
    
    def test_region_map_exists(self):
        """Test region mapping is defined."""
        fetcher = TrendsFetcher()
        assert "US" in fetcher.REGION_MAP
        assert "UK" in fetcher.REGION_MAP
        assert "DE" in fetcher.REGION_MAP
    
    def test_calculate_growth_rate_rising(self):
        """Test growth rate calculation for rising trend."""
        fetcher = TrendsFetcher()
        
        # Values increasing over time
        values = [10, 15, 20, 25, 30, 35, 40, 45]
        growth_rate = fetcher._calculate_growth_rate(values)
        
        assert growth_rate > 0  # Should be positive
    
    def test_calculate_growth_rate_declining(self):
        """Test growth rate calculation for declining trend."""
        fetcher = TrendsFetcher()
        
        # Values decreasing over time
        values = [45, 40, 35, 30, 25, 20, 15, 10]
        growth_rate = fetcher._calculate_growth_rate(values)
        
        assert growth_rate < 0  # Should be negative
    
    def test_calculate_growth_rate_stable(self):
        """Test growth rate calculation for stable trend."""
        fetcher = TrendsFetcher()
        
        # Values staying roughly the same
        values = [50, 51, 49, 50, 50, 51, 49, 50]
        growth_rate = fetcher._calculate_growth_rate(values)
        
        assert -10 <= growth_rate <= 10  # Should be near zero
    
    def test_calculate_growth_rate_empty(self):
        """Test growth rate calculation with empty values."""
        fetcher = TrendsFetcher()
        
        growth_rate = fetcher._calculate_growth_rate([])
        assert growth_rate == 0.0
        
        growth_rate = fetcher._calculate_growth_rate([50])
        assert growth_rate == 0.0
    
    def test_get_trend_direction_rising(self):
        """Test trend direction for rising growth."""
        fetcher = TrendsFetcher()
        
        assert fetcher._get_trend_direction(15.0) == "rising"
        assert fetcher._get_trend_direction(50.0) == "rising"
    
    def test_get_trend_direction_declining(self):
        """Test trend direction for declining growth."""
        fetcher = TrendsFetcher()
        
        assert fetcher._get_trend_direction(-15.0) == "declining"
        assert fetcher._get_trend_direction(-50.0) == "declining"
    
    def test_get_trend_direction_stable(self):
        """Test trend direction for stable growth."""
        fetcher = TrendsFetcher()
        
        assert fetcher._get_trend_direction(5.0) == "stable"
        assert fetcher._get_trend_direction(-5.0) == "stable"
        assert fetcher._get_trend_direction(0.0) == "stable"
    
    def test_calculate_search_volume(self):
        """Test search volume calculation."""
        fetcher = TrendsFetcher()
        
        # Uses most recent value scaled by 1000
        values = [50, 60, 70, 80]
        volume = fetcher._calculate_search_volume(values)
        assert volume == 80000  # 80 * 1000
        
        # Empty values
        volume = fetcher._calculate_search_volume([])
        assert volume == 0
    
    def test_build_cache_key(self):
        """Test cache key generation."""
        fetcher = TrendsFetcher()
        
        key1 = fetcher._build_cache_key(["fashion", "style"], "US", "30d")
        key2 = fetcher._build_cache_key(["fashion", "style"], "US", "30d")
        key3 = fetcher._build_cache_key(["style", "fashion"], "US", "30d")  # Same keywords, different order
        key4 = fetcher._build_cache_key(["electronics"], "US", "30d")
        
        assert key1 == key2  # Same params = same key
        assert key1 == key3  # Keywords are sorted, so order doesn't matter
        assert key1 != key4  # Different keywords = different key
        assert len(key1) == 16  # MD5 hash truncated to 16 chars
    
    def test_build_keyword_trends(self):
        """Test building KeywordTrend objects from raw data."""
        fetcher = TrendsFetcher()
        
        trends_data = {
            "interest_over_time": {
                "fashion": [30, 40, 50, 60, 70, 80, 90, 100],
            },
            "related_queries": {},
        }
        
        trends = fetcher._build_keyword_trends(trends_data, ["fashion"])
        
        assert len(trends) == 1
        assert trends[0].keyword == "fashion"
        assert trends[0].search_volume == 100000  # 100 * 1000
        assert trends[0].growth_rate > 0  # Rising trend
        assert trends[0].trend_direction == "rising"
    
    def test_analyze_seasonal_patterns_increasing(self):
        """Test seasonal pattern analysis for increasing trend."""
        fetcher = TrendsFetcher()
        
        # Need a significant increase (>20%) in recent values to trigger "increasing" pattern
        interest_data = {
            "keyword1": [30, 30, 30, 30, 30, 30, 80, 80, 80, 80, 80, 80, 80],  # Recent increase >20%
        }
        
        pattern = fetcher._analyze_seasonal_patterns(interest_data)
        assert "增加" in pattern or "increased" in pattern.lower()
    
    def test_analyze_seasonal_patterns_empty(self):
        """Test seasonal pattern analysis with empty data."""
        fetcher = TrendsFetcher()
        
        pattern = fetcher._analyze_seasonal_patterns({})
        assert "数据不足" in pattern or "Insufficient" in pattern


class TestTrendsFetcherIntegration:
    """Integration tests for TrendsFetcher (requires pytrends)."""
    
    def test_pytrends_import(self):
        """Test that pytrends can be imported."""
        try:
            from pytrends.request import TrendReq
            assert TrendReq is not None
        except ImportError:
            pytest.skip("pytrends not installed")
    
    def test_get_pytrends_instance(self):
        """Test getting pytrends instance."""
        try:
            fetcher = TrendsFetcher()
            pytrends = fetcher._get_pytrends()
            assert pytrends is not None
        except ImportError:
            pytest.skip("pytrends not installed")
        except Exception as e:
            # Skip if network is unavailable (e.g., ConnectTimeout)
            if "timeout" in str(e).lower() or "connection" in str(e).lower():
                pytest.skip(f"Network unavailable: {e}")
