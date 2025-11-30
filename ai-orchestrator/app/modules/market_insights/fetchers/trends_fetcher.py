"""
Google Trends data fetcher for Market Insights module.

Provides functionality to fetch market trends data using pytrends library
with rate limiting and caching support.

Requirements: 3.1, 3.2, 3.3, 3.4, 3.5
"""

import asyncio
import hashlib
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import structlog

from ..models import KeywordTrend, MarketTrendsResponse, TrendInsights
from ..utils.cache_manager import CacheManager
from ..utils.rate_limiter import RateLimiterRegistry
from ..utils.retry_strategy import (
    APIError,
    RateLimitError,
    RetryStrategy,
    TimeoutConfig,
)

logger = structlog.get_logger(__name__)

# Thread pool for running synchronous pytrends operations
_executor = ThreadPoolExecutor(max_workers=3)


class TrendsFetcher:
    """Google Trends data fetcher using pytrends.
    
    Fetches market trends data including search volume, growth rate,
    trend direction, and related queries.
    
    Note: pytrends is a synchronous library, so operations are run
    in a thread pool executor.
    
    Requirements: 3.1, 3.2, 3.3, 3.4, 3.5
    """
    
    # Time range mapping to pytrends timeframe format
    TIME_RANGE_MAP = {
        "1d": "now 1-d",
        "7d": "now 7-d",
        "30d": "today 1-m",
        "90d": "today 3-m",
        "1y": "today 12-m",
    }
    
    # Region code mapping
    REGION_MAP = {
        "US": "US",
        "UK": "GB",
        "DE": "DE",
        "FR": "FR",
        "JP": "JP",
        "CN": "CN",
        "KR": "KR",
        "AU": "AU",
        "CA": "CA",
        "BR": "BR",
        "IN": "IN",
        "MX": "MX",
        "ES": "ES",
        "IT": "IT",
        "NL": "NL",
    }
    
    def __init__(
        self,
        cache_manager: CacheManager | None = None,
    ):
        """Initialize trends fetcher.
        
        Args:
            cache_manager: Optional cache manager for caching results
        """
        self.cache_manager = cache_manager
        self.rate_limiter = RateLimiterRegistry.get_pytrends_limiter()
        self.retry_strategy = RetryStrategy(
            timeout=TimeoutConfig.PYTRENDS_TIMEOUT
        )
        self._pytrends = None
        
        logger.info("trends_fetcher_initialized")
    
    def _get_pytrends(self):
        """Get or create pytrends instance.
        
        Returns:
            TrendReq instance
        """
        if self._pytrends is None:
            try:
                from pytrends.request import TrendReq
                self._pytrends = TrendReq(hl="en-US", tz=360)
            except ImportError:
                logger.error("pytrends_not_installed")
                raise ImportError(
                    "pytrends is required. Install with: pip install pytrends"
                )
        return self._pytrends
    
    async def get_interest_over_time(
        self,
        keywords: list[str],
        region: str,
        time_range: str = "30d",
    ) -> MarketTrendsResponse:
        """Get keyword interest over time from Google Trends.
        
        Fetches search volume trends for specified keywords with
        growth rate calculation and trend direction analysis.
        
        Args:
            keywords: List of keywords to analyze (max 5)
            region: Region code (US, UK, DE, etc.)
            time_range: Time range (1d, 7d, 30d, 90d, 1y)
            
        Returns:
            MarketTrendsResponse with trends and insights
            
        Requirements: 3.1, 3.2, 3.3, 3.4, 3.5
        """
        log = logger.bind(
            keywords=keywords,
            region=region,
            time_range=time_range,
        )
        
        # Limit keywords to 5 (pytrends limitation)
        keywords = keywords[:5]
        
        # Build cache key
        cache_key = self._build_cache_key(keywords, region, time_range)
        
        # Try cache first
        if self.cache_manager:
            cached_data = await self.cache_manager.get(
                "market_trends",
                cache_key,
            )
            if cached_data:
                log.info("returning_cached_market_trends")
                return MarketTrendsResponse(**cached_data)
        
        # Fetch from pytrends
        try:
            trends_data = await self._fetch_trends(
                keywords=keywords,
                region=region,
                time_range=time_range,
            )
            
            # Build response
            trends = self._build_keyword_trends(trends_data, keywords)
            insights = self._generate_insights(trends_data, keywords)
            
            response = MarketTrendsResponse(
                status="success",
                trends=trends,
                insights=insights,
            )
            
            # Cache the result
            if self.cache_manager:
                await self.cache_manager.set_with_stale(
                    "market_trends",
                    cache_key,
                    response.model_dump(),
                )
            
            log.info(
                "market_trends_fetched",
                trend_count=len(trends),
            )
            return response
            
        except Exception as e:
            log.error("market_trends_fetch_failed", error=str(e))
            
            # Try stale cache as fallback
            if self.cache_manager:
                stale_data = await self.cache_manager.get_stale_cache(
                    "market_trends",
                    cache_key,
                    max_age=259200,  # 3 days
                )
                if stale_data:
                    log.warning("returning_stale_cached_trends")
                    response = MarketTrendsResponse(**stale_data)
                    response.degraded = True
                    response.message = "使用缓存数据，数据可能不是最新 / Using cached data"
                    return response
            
            return MarketTrendsResponse(
                status="error",
                trends=[],
                insights=None,
                message=f"获取市场趋势失败: {str(e)} / Failed to fetch market trends",
            )
    
    async def get_related_queries(
        self,
        keyword: str,
        region: str,
    ) -> dict[str, Any]:
        """Get related queries for a keyword.
        
        Args:
            keyword: Keyword to analyze
            region: Region code
            
        Returns:
            Dict with related queries (top and rising)
        """
        log = logger.bind(keyword=keyword, region=region)
        
        try:
            # Acquire rate limit
            await self.rate_limiter.acquire()
            
            # Run in thread pool
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                _executor,
                self._fetch_related_queries_sync,
                keyword,
                region,
            )
            
            log.info("related_queries_fetched")
            return {
                "status": "success",
                "related_queries": result,
            }
            
        except Exception as e:
            log.error("related_queries_fetch_failed", error=str(e))
            return {
                "status": "error",
                "message": f"获取相关查询失败: {str(e)} / Failed to fetch related queries",
            }
    
    async def _fetch_trends(
        self,
        keywords: list[str],
        region: str,
        time_range: str,
    ) -> dict[str, Any]:
        """Internal method to fetch trends data.
        
        Args:
            keywords: Keywords to analyze
            region: Region code
            time_range: Time range
            
        Returns:
            Dict with interest_over_time and related_queries data
        """
        # Acquire rate limit
        await self.rate_limiter.acquire()
        
        # Convert parameters
        geo = self.REGION_MAP.get(region.upper(), region.upper())
        timeframe = self.TIME_RANGE_MAP.get(time_range, "today 1-m")
        
        # Run synchronous pytrends in thread pool
        loop = asyncio.get_event_loop()
        
        async def fetch():
            return await loop.run_in_executor(
                _executor,
                self._fetch_trends_sync,
                keywords,
                geo,
                timeframe,
            )
        
        return await self.retry_strategy.execute(
            fetch,
            context="pytrends_interest_over_time",
        )
    
    def _fetch_trends_sync(
        self,
        keywords: list[str],
        geo: str,
        timeframe: str,
    ) -> dict[str, Any]:
        """Synchronous method to fetch trends (runs in thread pool).
        
        Args:
            keywords: Keywords to analyze
            geo: Geographic region code
            timeframe: pytrends timeframe string
            
        Returns:
            Dict with trends data
        """
        pytrends = self._get_pytrends()
        
        try:
            # Build payload
            pytrends.build_payload(
                kw_list=keywords,
                geo=geo,
                timeframe=timeframe,
            )
            
            # Get interest over time
            interest_df = pytrends.interest_over_time()
            
            # Get related queries
            related = pytrends.related_queries()
            
            # Convert DataFrame to dict
            interest_data = {}
            if not interest_df.empty:
                for keyword in keywords:
                    if keyword in interest_df.columns:
                        values = interest_df[keyword].tolist()
                        interest_data[keyword] = values
            
            return {
                "interest_over_time": interest_data,
                "related_queries": related,
            }
            
        except Exception as e:
            error_msg = str(e).lower()
            if "429" in error_msg or "rate" in error_msg:
                raise RateLimitError("Google Trends rate limit exceeded")
            raise APIError(f"pytrends error: {str(e)}")
    
    def _fetch_related_queries_sync(
        self,
        keyword: str,
        region: str,
    ) -> dict[str, list[str]]:
        """Synchronous method to fetch related queries.
        
        Args:
            keyword: Keyword to analyze
            region: Region code
            
        Returns:
            Dict with top and rising queries
        """
        pytrends = self._get_pytrends()
        geo = self.REGION_MAP.get(region.upper(), region.upper())
        
        pytrends.build_payload(
            kw_list=[keyword],
            geo=geo,
            timeframe="today 1-m",
        )
        
        related = pytrends.related_queries()
        
        result = {
            "top": [],
            "rising": [],
        }
        
        if keyword in related:
            keyword_data = related[keyword]
            
            if keyword_data.get("top") is not None:
                top_df = keyword_data["top"]
                if not top_df.empty:
                    result["top"] = top_df["query"].tolist()[:10]
            
            if keyword_data.get("rising") is not None:
                rising_df = keyword_data["rising"]
                if not rising_df.empty:
                    result["rising"] = rising_df["query"].tolist()[:10]
        
        return result
    
    def _build_keyword_trends(
        self,
        trends_data: dict[str, Any],
        keywords: list[str],
    ) -> list[KeywordTrend]:
        """Build KeywordTrend objects from raw data.
        
        Args:
            trends_data: Raw trends data from pytrends
            keywords: Original keywords list
            
        Returns:
            List of KeywordTrend objects
            
        Requirements: 3.2, 3.3
        """
        trends = []
        interest_data = trends_data.get("interest_over_time", {})
        related_data = trends_data.get("related_queries", {})
        
        for keyword in keywords:
            values = interest_data.get(keyword, [])
            
            # Calculate metrics
            search_volume = self._calculate_search_volume(values)
            growth_rate = self._calculate_growth_rate(values)
            trend_direction = self._get_trend_direction(growth_rate)
            related_queries = self._extract_related_queries(
                related_data,
                keyword,
            )
            
            trend = KeywordTrend(
                keyword=keyword,
                search_volume=search_volume,
                growth_rate=growth_rate,
                trend_direction=trend_direction,
                related_queries=related_queries,
            )
            trends.append(trend)
        
        return trends
    
    def _calculate_search_volume(self, values: list[int]) -> int:
        """Calculate representative search volume.
        
        Uses the most recent value as the search volume indicator.
        Google Trends returns relative values (0-100), so we scale them.
        
        Args:
            values: List of interest values over time
            
        Returns:
            Estimated search volume
        """
        if not values:
            return 0
        
        # Use the most recent value, scaled to represent volume
        recent_value = values[-1] if values else 0
        # Scale factor to convert relative interest to estimated volume
        return int(recent_value * 1000)
    
    def _calculate_growth_rate(self, values: list[int]) -> float:
        """Calculate growth rate from time series data.
        
        Compares the average of the first half to the second half
        of the time period.
        
        Args:
            values: List of interest values over time
            
        Returns:
            Growth rate as percentage
            
        Requirements: 3.3
        """
        if len(values) < 2:
            return 0.0
        
        mid_point = len(values) // 2
        first_half = values[:mid_point]
        second_half = values[mid_point:]
        
        if not first_half or not second_half:
            return 0.0
        
        first_avg = sum(first_half) / len(first_half)
        second_avg = sum(second_half) / len(second_half)
        
        if first_avg == 0:
            return 100.0 if second_avg > 0 else 0.0
        
        growth_rate = ((second_avg - first_avg) / first_avg) * 100
        return round(growth_rate, 2)
    
    def _get_trend_direction(self, growth_rate: float) -> str:
        """Determine trend direction from growth rate.
        
        Args:
            growth_rate: Growth rate percentage
            
        Returns:
            Trend direction: "rising", "stable", or "declining"
            
        Requirements: 3.3
        """
        if growth_rate > 10:
            return "rising"
        elif growth_rate < -10:
            return "declining"
        return "stable"
    
    def _extract_related_queries(
        self,
        related_data: dict[str, Any],
        keyword: str,
    ) -> list[str]:
        """Extract related queries for a keyword.
        
        Args:
            related_data: Related queries data from pytrends
            keyword: Keyword to extract queries for
            
        Returns:
            List of related query strings
            
        Requirements: 3.5
        """
        queries = []
        
        if keyword not in related_data:
            return queries
        
        keyword_data = related_data[keyword]
        
        # Get top queries
        if keyword_data.get("top") is not None:
            top_df = keyword_data["top"]
            if hasattr(top_df, "empty") and not top_df.empty:
                queries.extend(top_df["query"].tolist()[:5])
        
        # Get rising queries
        if keyword_data.get("rising") is not None:
            rising_df = keyword_data["rising"]
            if hasattr(rising_df, "empty") and not rising_df.empty:
                rising_queries = rising_df["query"].tolist()[:5]
                for q in rising_queries:
                    if q not in queries:
                        queries.append(q)
        
        return queries[:10]  # Limit to 10 related queries
    
    def _generate_insights(
        self,
        trends_data: dict[str, Any],
        keywords: list[str],
    ) -> TrendInsights:
        """Generate trend insights from data.
        
        Args:
            trends_data: Raw trends data
            keywords: Original keywords
            
        Returns:
            TrendInsights object
            
        Requirements: 3.4, 3.5
        """
        interest_data = trends_data.get("interest_over_time", {})
        related_data = trends_data.get("related_queries", {})
        
        # Identify hot topics (keywords with high recent interest)
        hot_topics = []
        for keyword in keywords:
            values = interest_data.get(keyword, [])
            if values and values[-1] > 50:  # High recent interest
                hot_topics.append(keyword)
        
        # Identify emerging trends (keywords with high growth)
        emerging_trends = []
        for keyword in keywords:
            values = interest_data.get(keyword, [])
            growth = self._calculate_growth_rate(values)
            if growth > 20:  # Significant growth
                emerging_trends.append(keyword)
        
        # Add rising related queries as emerging trends
        for keyword in keywords:
            if keyword in related_data:
                keyword_data = related_data[keyword]
                if keyword_data.get("rising") is not None:
                    rising_df = keyword_data["rising"]
                    if hasattr(rising_df, "empty") and not rising_df.empty:
                        rising_queries = rising_df["query"].tolist()[:3]
                        for q in rising_queries:
                            if q not in emerging_trends:
                                emerging_trends.append(q)
        
        # Generate seasonal patterns description
        seasonal_patterns = self._analyze_seasonal_patterns(interest_data)
        
        return TrendInsights(
            hot_topics=hot_topics[:5],
            emerging_trends=emerging_trends[:5],
            seasonal_patterns=seasonal_patterns,
        )
    
    def _analyze_seasonal_patterns(
        self,
        interest_data: dict[str, list[int]],
    ) -> str:
        """Analyze seasonal patterns in the data.
        
        Args:
            interest_data: Interest over time data
            
        Returns:
            Description of seasonal patterns
        """
        if not interest_data:
            return "数据不足，无法分析季节性模式 / Insufficient data for seasonal analysis"
        
        # Calculate overall trend
        all_values = []
        for values in interest_data.values():
            all_values.extend(values)
        
        if not all_values:
            return "数据不足，无法分析季节性模式 / Insufficient data for seasonal analysis"
        
        avg_value = sum(all_values) / len(all_values)
        recent_values = all_values[-7:] if len(all_values) >= 7 else all_values
        recent_avg = sum(recent_values) / len(recent_values)
        
        if recent_avg > avg_value * 1.2:
            return "近期搜索量增加 20% 以上 / Recent search volume increased by 20%+"
        elif recent_avg < avg_value * 0.8:
            return "近期搜索量下降 20% 以上 / Recent search volume decreased by 20%+"
        else:
            return "搜索量保持稳定 / Search volume remains stable"
    
    def _build_cache_key(
        self,
        keywords: list[str],
        region: str,
        time_range: str,
    ) -> str:
        """Build cache key for trends request.
        
        Args:
            keywords: Keywords list
            region: Region code
            time_range: Time range
            
        Returns:
            Cache key string
        """
        key_parts = f"{':'.join(sorted(keywords))}:{region}:{time_range}"
        return hashlib.md5(key_parts.encode()).hexdigest()[:16]
