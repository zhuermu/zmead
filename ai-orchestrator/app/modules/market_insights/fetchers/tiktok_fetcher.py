"""
TikTok Creative Center API fetcher for Market Insights module.

Provides functionality to fetch trending creatives and creative details
from TikTok Creative Center API.

Requirements: 2.1, 2.2, 2.3
"""

import hashlib
from typing import Any

import aiohttp
import structlog

from ..models import TrendingCreative, TrendingCreativesResponse
from ..utils.cache_manager import CacheManager
from ..utils.rate_limiter import RateLimiterRegistry
from ..utils.retry_strategy import (
    APIError,
    RateLimitError,
    RetryStrategy,
    TimeoutConfig,
)

logger = structlog.get_logger(__name__)


class TikTokFetcher:
    """TikTok Creative Center API data fetcher.
    
    Fetches trending creatives and creative details from TikTok's
    Creative Center API with caching and retry support.
    
    Requirements: 2.1, 2.2, 2.3
    """
    
    # TikTok Creative Center API base URL
    BASE_URL = "https://business-api.tiktok.com/open_api/v1.3"
    
    # Industry ID mapping
    INDUSTRY_MAP = {
        "fashion": "1001",
        "electronics": "1002",
        "beauty": "1003",
        "home": "1004",
        "food": "1005",
        "sports": "1006",
        "travel": "1007",
        "automotive": "1008",
        "finance": "1009",
        "education": "1010",
        "gaming": "1011",
        "entertainment": "1012",
    }
    
    # Time range mapping
    TIME_RANGE_MAP = {
        "1d": 1,
        "7d": 7,
        "30d": 30,
    }
    
    def __init__(
        self,
        api_key: str,
        api_secret: str,
        cache_manager: CacheManager | None = None,
    ):
        """Initialize TikTok fetcher.
        
        Args:
            api_key: TikTok API key (app_id)
            api_secret: TikTok API secret
            cache_manager: Optional cache manager for caching results
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.cache_manager = cache_manager
        self.rate_limiter = RateLimiterRegistry.get_tiktok_limiter()
        self.retry_strategy = RetryStrategy(
            timeout=TimeoutConfig.TIKTOK_API_TIMEOUT
        )
        self._access_token: str | None = None
        
        logger.info("tiktok_fetcher_initialized")
    
    async def get_trending_creatives(
        self,
        industry: str,
        region: str,
        time_range: str = "7d",
        limit: int = 20,
    ) -> TrendingCreativesResponse:
        """Get trending creatives from TikTok Creative Center.
        
        Fetches popular ad creatives filtered by industry and region.
        Results are cached for 12 hours.
        
        Args:
            industry: Industry category (fashion, electronics, etc.)
            region: Region code (US, UK, DE, etc.)
            time_range: Time range for trending data (1d, 7d, 30d)
            limit: Maximum number of creatives to return (1-50)
            
        Returns:
            TrendingCreativesResponse with list of trending creatives
            
        Requirements: 2.1, 2.2, 2.3
        """
        log = logger.bind(
            industry=industry,
            region=region,
            time_range=time_range,
            limit=limit,
        )
        
        # Build cache key
        cache_key = self._build_cache_key(industry, region, time_range, limit)
        
        # Try cache first
        if self.cache_manager:
            cached_data = await self.cache_manager.get(
                "trending_creatives",
                cache_key,
            )
            if cached_data:
                log.info("returning_cached_trending_creatives")
                return TrendingCreativesResponse(**cached_data)
        
        # Fetch from API
        try:
            creatives = await self._fetch_trending_creatives(
                industry=industry,
                region=region,
                time_range=time_range,
                limit=limit,
            )
            
            response = TrendingCreativesResponse(
                status="success",
                creatives=creatives,
                total=len(creatives),
            )
            
            # Cache the result
            if self.cache_manager:
                await self.cache_manager.set_with_stale(
                    "trending_creatives",
                    cache_key,
                    response.model_dump(),
                )
            
            log.info(
                "trending_creatives_fetched",
                count=len(creatives),
            )
            return response
            
        except Exception as e:
            log.error("trending_creatives_fetch_failed", error=str(e))
            
            # Try stale cache as fallback
            if self.cache_manager:
                stale_data = await self.cache_manager.get_stale_cache(
                    "trending_creatives",
                    cache_key,
                    max_age=604800,  # 7 days
                )
                if stale_data:
                    log.warning("returning_stale_cached_creatives")
                    response = TrendingCreativesResponse(**stale_data)
                    response.degraded = True
                    response.message = "使用缓存数据，数据可能不是最新 / Using cached data"
                    return response
            
            return TrendingCreativesResponse(
                status="error",
                creatives=[],
                total=0,
                message=f"获取热门素材失败: {str(e)} / Failed to fetch trending creatives",
            )
    
    async def get_creative_details(
        self,
        creative_id: str,
    ) -> dict[str, Any]:
        """Get detailed information about a specific creative.
        
        Args:
            creative_id: TikTok creative ID
            
        Returns:
            Dict with creative details
        """
        log = logger.bind(creative_id=creative_id)
        
        try:
            details = await self._fetch_creative_details(creative_id)
            log.info("creative_details_fetched")
            return {
                "status": "success",
                "details": details,
            }
        except Exception as e:
            log.error("creative_details_fetch_failed", error=str(e))
            return {
                "status": "error",
                "message": f"获取素材详情失败: {str(e)} / Failed to fetch creative details",
            }
    
    async def _fetch_trending_creatives(
        self,
        industry: str,
        region: str,
        time_range: str,
        limit: int,
    ) -> list[TrendingCreative]:
        """Internal method to fetch trending creatives from API.
        
        Args:
            industry: Industry category
            region: Region code
            time_range: Time range
            limit: Maximum results
            
        Returns:
            List of TrendingCreative objects
        """
        # Acquire rate limit
        await self.rate_limiter.acquire()
        
        # Get access token
        access_token = await self._get_access_token()
        
        # Build request parameters
        industry_id = self.INDUSTRY_MAP.get(industry.lower(), "1001")
        period = self.TIME_RANGE_MAP.get(time_range, 7)
        
        params = {
            "industry_id": industry_id,
            "country_code": region.upper(),
            "period": period,
            "page_size": min(limit, 50),
            "page": 1,
        }
        
        headers = {
            "Access-Token": access_token,
            "Content-Type": "application/json",
        }
        
        # Execute with retry
        async def fetch():
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.BASE_URL}/creative/trending/list/",
                    headers=headers,
                    params=params,
                    timeout=aiohttp.ClientTimeout(
                        total=TimeoutConfig.TIKTOK_API_TIMEOUT
                    ),
                ) as response:
                    if response.status == 429:
                        raise RateLimitError("TikTok API rate limit exceeded")
                    if response.status != 200:
                        raise APIError(
                            f"TikTok API error: {response.status}",
                            status_code=response.status,
                        )
                    
                    data = await response.json()
                    return data
        
        result = await self.retry_strategy.execute(
            fetch,
            context="tiktok_trending_creatives",
        )
        
        # Transform response to standard format
        return self._transform_creatives(result.get("data", {}).get("list", []))
    
    async def _fetch_creative_details(
        self,
        creative_id: str,
    ) -> dict[str, Any]:
        """Internal method to fetch creative details from API.
        
        Args:
            creative_id: Creative ID
            
        Returns:
            Creative details dict
        """
        # Acquire rate limit
        await self.rate_limiter.acquire()
        
        # Get access token
        access_token = await self._get_access_token()
        
        headers = {
            "Access-Token": access_token,
            "Content-Type": "application/json",
        }
        
        params = {
            "creative_id": creative_id,
        }
        
        async def fetch():
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.BASE_URL}/creative/detail/",
                    headers=headers,
                    params=params,
                    timeout=aiohttp.ClientTimeout(
                        total=TimeoutConfig.TIKTOK_API_TIMEOUT
                    ),
                ) as response:
                    if response.status == 429:
                        raise RateLimitError("TikTok API rate limit exceeded")
                    if response.status != 200:
                        raise APIError(
                            f"TikTok API error: {response.status}",
                            status_code=response.status,
                        )
                    
                    data = await response.json()
                    return data.get("data", {})
        
        return await self.retry_strategy.execute(
            fetch,
            context="tiktok_creative_details",
        )
    
    async def _get_access_token(self) -> str:
        """Get or refresh TikTok API access token.
        
        Returns:
            Valid access token string
        """
        if self._access_token:
            return self._access_token
        
        # Request new access token
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.BASE_URL}/oauth2/access_token/",
                json={
                    "app_id": self.api_key,
                    "secret": self.api_secret,
                },
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                if response.status != 200:
                    raise APIError(
                        f"Failed to get access token: {response.status}",
                        status_code=response.status,
                    )
                
                data = await response.json()
                self._access_token = data.get("data", {}).get("access_token")
                
                if not self._access_token:
                    raise APIError("No access token in response")
                
                logger.info("tiktok_access_token_obtained")
                return self._access_token
    
    def _transform_creatives(
        self,
        raw_list: list[dict[str, Any]],
    ) -> list[TrendingCreative]:
        """Transform API response to standard TrendingCreative format.
        
        Args:
            raw_list: Raw API response list
            
        Returns:
            List of TrendingCreative objects
            
        Requirements: 2.3
        """
        creatives = []
        
        for item in raw_list:
            try:
                creative = TrendingCreative(
                    id=str(item.get("creative_id", item.get("id", ""))),
                    title=item.get("title", item.get("name", "Untitled")),
                    thumbnail_url=item.get(
                        "thumbnail_url",
                        item.get("cover_url", ""),
                    ),
                    views=int(item.get("play_count", item.get("views", 0))),
                    engagement_rate=float(
                        item.get("engagement_rate", item.get("ctr", 0.0))
                    ),
                    platform="tiktok",
                )
                creatives.append(creative)
            except Exception as e:
                logger.warning(
                    "creative_transform_failed",
                    item_id=item.get("creative_id"),
                    error=str(e),
                )
                continue
        
        return creatives
    
    def _build_cache_key(
        self,
        industry: str,
        region: str,
        time_range: str,
        limit: int,
    ) -> str:
        """Build cache key for trending creatives request.
        
        Args:
            industry: Industry category
            region: Region code
            time_range: Time range
            limit: Result limit
            
        Returns:
            Cache key string
        """
        key_parts = f"{industry}:{region}:{time_range}:{limit}"
        return hashlib.md5(key_parts.encode()).hexdigest()[:16]
