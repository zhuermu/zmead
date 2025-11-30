"""
Degradation handling for Market Insights module.

This module provides graceful degradation strategies when third-party APIs
(TikTok Creative Center, pytrends) are unavailable, using stale cache data
or AI-generated fallbacks.

Requirements: 6.4, 6.6
"""

from datetime import datetime
from typing import Any, Callable

import structlog

from app.modules.market_insights.utils.cache_manager import CacheManager

logger = structlog.get_logger(__name__)


class DegradationHandler:
    """
    Handles graceful degradation when third-party APIs are unavailable.

    Provides fallback strategies:
    - TikTok API unavailable: Use stale cache (up to 7 days)
    - Google Trends unavailable: Use stale cache (up to 3 days) or AI fallback
    - General API failures: Return degraded response with available data

    Requirements: 6.4, 6.6
    """

    # Maximum stale cache ages in seconds
    MAX_STALE_AGE_TIKTOK = 604800  # 7 days
    MAX_STALE_AGE_TRENDS = 259200  # 3 days
    MAX_STALE_AGE_COMPETITOR = 86400  # 1 day

    def __init__(
        self,
        cache_manager: CacheManager,
        gemini_client: Any | None = None,
    ):
        """
        Initialize degradation handler.

        Args:
            cache_manager: Cache manager instance for stale cache access
            gemini_client: Optional Gemini client for AI fallback generation
        """
        self.cache_manager = cache_manager
        self.gemini_client = gemini_client

        logger.info(
            "degradation_handler_initialized",
            max_stale_tiktok=self.MAX_STALE_AGE_TIKTOK,
            max_stale_trends=self.MAX_STALE_AGE_TRENDS,
            has_gemini_client=gemini_client is not None,
        )

    async def handle_tiktok_unavailable(
        self,
        cache_key: str,
        industry: str | None = None,
        region: str | None = None,
    ) -> dict[str, Any]:
        """
        Handle TikTok Creative Center API unavailability.

        Attempts to use stale cache data (up to 7 days old).
        If no cache available, returns error with degraded flag.

        Args:
            cache_key: Cache key for the trending creatives data
            industry: Optional industry for context
            region: Optional region for context

        Returns:
            Response dict with:
            - status: "success" or "error"
            - data: Cached data if available
            - degraded: True if using fallback
            - message: User-friendly message about data freshness

        Requirements: 6.4, 6.6
        """
        log = logger.bind(
            cache_key=cache_key,
            industry=industry,
            region=region,
        )

        log.info("handling_tiktok_unavailable")

        # Try to get stale cache data (up to 7 days)
        cached_data = await self.cache_manager.get_stale_cache(
            cache_type="trending_creatives",
            key=cache_key,
            max_age=self.MAX_STALE_AGE_TIKTOK,
        )

        if cached_data:
            log.info(
                "tiktok_stale_cache_hit",
                data_count=len(cached_data.get("creatives", [])) if isinstance(cached_data, dict) else 0,
            )
            return {
                "status": "success",
                "data": cached_data,
                "degraded": True,
                "degradation_reason": "tiktok_api_unavailable",
                "message": "使用缓存数据，数据可能不是最新",
                "message_en": "Using cached data, data may not be current",
                "timestamp": datetime.utcnow().isoformat(),
            }

        # No cache available
        log.warning("tiktok_no_cache_available")
        return {
            "status": "error",
            "error_code": "4002",
            "degraded": True,
            "degradation_reason": "tiktok_api_unavailable_no_cache",
            "message": "热门素材数据暂时不可用，请稍后重试",
            "message_en": "Trending creatives data temporarily unavailable, please try again later",
            "retry_allowed": True,
            "retry_after": 300,  # 5 minutes
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def handle_trends_unavailable(
        self,
        cache_key: str,
        keywords: list[str] | None = None,
        region: str | None = None,
    ) -> dict[str, Any]:
        """
        Handle Google Trends (pytrends) unavailability.

        Attempts to:
        1. Use stale cache data (up to 3 days old)
        2. Generate AI-based trend analysis as fallback

        Args:
            cache_key: Cache key for the market trends data
            keywords: Optional keywords for AI fallback generation
            region: Optional region for context

        Returns:
            Response dict with:
            - status: "success" or "error"
            - data: Cached or AI-generated data if available
            - degraded: True if using fallback
            - message: User-friendly message about data source

        Requirements: 6.4, 6.6
        """
        log = logger.bind(
            cache_key=cache_key,
            keywords=keywords,
            region=region,
        )

        log.info("handling_trends_unavailable")

        # Try to get stale cache data (up to 3 days)
        cached_data = await self.cache_manager.get_stale_cache(
            cache_type="market_trends",
            key=cache_key,
            max_age=self.MAX_STALE_AGE_TRENDS,
        )

        if cached_data:
            log.info(
                "trends_stale_cache_hit",
                data_count=len(cached_data.get("trends", [])) if isinstance(cached_data, dict) else 0,
            )
            return {
                "status": "success",
                "data": cached_data,
                "degraded": True,
                "degradation_reason": "pytrends_unavailable_cache_fallback",
                "message": "使用缓存数据，数据可能不是最新",
                "message_en": "Using cached data, data may not be current",
                "timestamp": datetime.utcnow().isoformat(),
            }

        # Try AI fallback if Gemini client is available
        if self.gemini_client and keywords:
            log.info("attempting_ai_trend_fallback", keywords=keywords)
            try:
                ai_trends = await self._generate_ai_trend_analysis(keywords, region)
                if ai_trends:
                    log.info("ai_trend_fallback_success")
                    return {
                        "status": "success",
                        "data": ai_trends,
                        "degraded": True,
                        "degradation_reason": "pytrends_unavailable_ai_fallback",
                        "message": "基于 AI 分析生成的趋势数据",
                        "message_en": "Trend data generated by AI analysis",
                        "timestamp": datetime.utcnow().isoformat(),
                    }
            except Exception as e:
                log.warning("ai_trend_fallback_failed", error=str(e))

        # No fallback available
        log.warning("trends_no_fallback_available")
        return {
            "status": "error",
            "error_code": "4002",
            "degraded": True,
            "degradation_reason": "pytrends_unavailable_no_fallback",
            "message": "市场趋势数据暂时不可用，请稍后重试",
            "message_en": "Market trends data temporarily unavailable, please try again later",
            "retry_allowed": True,
            "retry_after": 300,  # 5 minutes
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def handle_competitor_analysis_unavailable(
        self,
        cache_key: str,
        competitor_url: str | None = None,
    ) -> dict[str, Any]:
        """
        Handle competitor analysis unavailability.

        Attempts to use stale cache data (up to 1 day old).

        Args:
            cache_key: Cache key for the competitor analysis data
            competitor_url: Optional competitor URL for context

        Returns:
            Response dict with degraded data or error

        Requirements: 6.4, 6.6
        """
        log = logger.bind(
            cache_key=cache_key,
            competitor_url=competitor_url,
        )

        log.info("handling_competitor_analysis_unavailable")

        # Try to get stale cache data (up to 1 day)
        cached_data = await self.cache_manager.get_stale_cache(
            cache_type="competitor_analysis",
            key=cache_key,
            max_age=self.MAX_STALE_AGE_COMPETITOR,
        )

        if cached_data:
            log.info("competitor_stale_cache_hit")
            return {
                "status": "success",
                "data": cached_data,
                "degraded": True,
                "degradation_reason": "competitor_analysis_unavailable_cache_fallback",
                "message": "使用缓存的竞品分析数据",
                "message_en": "Using cached competitor analysis data",
                "timestamp": datetime.utcnow().isoformat(),
            }

        # No cache available
        log.warning("competitor_no_cache_available")
        return {
            "status": "error",
            "error_code": "4001",
            "degraded": True,
            "degradation_reason": "competitor_analysis_unavailable_no_cache",
            "message": "竞品分析暂时不可用，请稍后重试",
            "message_en": "Competitor analysis temporarily unavailable, please try again later",
            "retry_allowed": True,
            "retry_after": 60,  # 1 minute
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def handle_api_rate_limit(
        self,
        api_source: str,
        retry_after: int = 60,
        cache_key: str | None = None,
        cache_type: str | None = None,
    ) -> dict[str, Any]:
        """
        Handle API rate limit exceeded.

        Attempts to use stale cache if available, otherwise returns
        rate limit error with retry information.

        Args:
            api_source: Name of the API that hit rate limit
            retry_after: Seconds to wait before retry
            cache_key: Optional cache key to try stale cache
            cache_type: Optional cache type for stale cache lookup

        Returns:
            Response dict with degraded data or rate limit error

        Requirements: 6.4
        """
        log = logger.bind(
            api_source=api_source,
            retry_after=retry_after,
            cache_key=cache_key,
        )

        log.warning("handling_api_rate_limit")

        # Try stale cache if key provided
        if cache_key and cache_type:
            max_age = self._get_max_stale_age(cache_type)
            cached_data = await self.cache_manager.get_stale_cache(
                cache_type=cache_type,
                key=cache_key,
                max_age=max_age,
            )

            if cached_data:
                log.info("rate_limit_stale_cache_hit", cache_type=cache_type)
                return {
                    "status": "success",
                    "data": cached_data,
                    "degraded": True,
                    "degradation_reason": f"{api_source}_rate_limit_cache_fallback",
                    "message": f"API 请求频率受限，使用缓存数据",
                    "message_en": f"API rate limited, using cached data",
                    "timestamp": datetime.utcnow().isoformat(),
                }

        # No cache available, return rate limit error
        return {
            "status": "error",
            "error_code": "1003",
            "degraded": True,
            "degradation_reason": f"{api_source}_rate_limit",
            "message": "请求过于频繁，请稍后重试",
            "message_en": "Too many requests, please try again later",
            "retry_allowed": True,
            "retry_after": retry_after,
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def execute_with_degradation(
        self,
        primary_func: Callable,
        degradation_handler: Callable,
        context: str = "operation",
    ) -> dict[str, Any]:
        """
        Execute a function with automatic degradation on failure.

        Attempts to execute the primary function. If it fails,
        calls the degradation handler to provide fallback data.

        Args:
            primary_func: Primary async function to execute
            degradation_handler: Async function to call on failure
            context: Context string for logging

        Returns:
            Result from primary function or degradation handler

        Requirements: 6.4, 6.6
        """
        log = logger.bind(context=context)

        try:
            log.debug("executing_primary_function")
            result = await primary_func()
            return result

        except Exception as e:
            log.warning(
                "primary_function_failed_attempting_degradation",
                error=str(e),
                error_type=type(e).__name__,
            )

            try:
                degraded_result = await degradation_handler()
                return degraded_result

            except Exception as degradation_error:
                log.error(
                    "degradation_handler_failed",
                    error=str(degradation_error),
                    original_error=str(e),
                )
                # Return the original error
                raise e

    async def _generate_ai_trend_analysis(
        self,
        keywords: list[str],
        region: str | None = None,
    ) -> dict[str, Any] | None:
        """
        Generate AI-based trend analysis as fallback.

        Uses Gemini to generate trend insights based on keywords
        when Google Trends API is unavailable.

        Args:
            keywords: Keywords to analyze
            region: Optional region for context

        Returns:
            AI-generated trend data or None if generation fails
        """
        if not self.gemini_client:
            return None

        log = logger.bind(keywords=keywords, region=region)

        try:
            prompt = f"""
基于你对市场趋势的了解，为以下关键词生成趋势分析：

关键词：{', '.join(keywords)}
地区：{region or '全球'}

请以 JSON 格式返回，包含以下字段：
- trends: 关键词趋势列表，每个包含 keyword, trend_direction (rising/stable/declining), estimated_interest (1-100)
- insights: 包含 hot_topics, emerging_trends, seasonal_patterns
- note: 说明这是基于 AI 分析的估计数据

注意：这是在 Google Trends API 不可用时的备用分析，请基于你的知识提供合理的估计。
"""

            response = await self.gemini_client.generate_content(prompt)

            # Parse the response
            import json
            try:
                # Try to extract JSON from the response
                response_text = response.text if hasattr(response, 'text') else str(response)
                # Find JSON in the response
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}') + 1
                if start_idx != -1 and end_idx > start_idx:
                    json_str = response_text[start_idx:end_idx]
                    ai_data = json.loads(json_str)
                    ai_data["ai_generated"] = True
                    ai_data["generation_timestamp"] = datetime.utcnow().isoformat()
                    return ai_data
            except json.JSONDecodeError:
                log.warning("ai_response_json_parse_failed")
                return None

        except Exception as e:
            log.error("ai_trend_generation_failed", error=str(e))
            return None

    def _get_max_stale_age(self, cache_type: str) -> int:
        """
        Get maximum stale cache age for a cache type.

        Args:
            cache_type: Type of cache

        Returns:
            Maximum age in seconds
        """
        stale_ages = {
            "trending_creatives": self.MAX_STALE_AGE_TIKTOK,
            "market_trends": self.MAX_STALE_AGE_TRENDS,
            "competitor_analysis": self.MAX_STALE_AGE_COMPETITOR,
        }
        return stale_ages.get(cache_type, 86400)  # Default 1 day

    def create_degraded_response(
        self,
        data: dict[str, Any] | None,
        degradation_reason: str,
        message: str,
        message_en: str,
    ) -> dict[str, Any]:
        """
        Create a standardized degraded response.

        Args:
            data: Available data (may be partial or stale)
            degradation_reason: Reason for degradation
            message: User-friendly message in Chinese
            message_en: User-friendly message in English

        Returns:
            Standardized degraded response dict
        """
        if data:
            return {
                "status": "success",
                "data": data,
                "degraded": True,
                "degradation_reason": degradation_reason,
                "message": message,
                "message_en": message_en,
                "timestamp": datetime.utcnow().isoformat(),
            }
        else:
            return {
                "status": "error",
                "error_code": "4002",
                "degraded": True,
                "degradation_reason": degradation_reason,
                "message": message,
                "message_en": message_en,
                "retry_allowed": True,
                "timestamp": datetime.utcnow().isoformat(),
            }

    @staticmethod
    def is_degraded_response(response: dict[str, Any]) -> bool:
        """
        Check if a response is degraded.

        Args:
            response: Response dict to check

        Returns:
            True if response is degraded
        """
        return response.get("degraded", False)

    @staticmethod
    def get_degradation_reason(response: dict[str, Any]) -> str | None:
        """
        Get the degradation reason from a response.

        Args:
            response: Response dict

        Returns:
            Degradation reason string or None
        """
        return response.get("degradation_reason")
