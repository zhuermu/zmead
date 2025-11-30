"""
Cache manager for Ad Creative module.

Provides caching functionality for product information and analysis results
to reduce API calls and improve performance.

Requirements: Non-functional requirements - Cost control
- Product information cache: 1 hour TTL
- Analysis results cache: 24 hours TTL
"""

import hashlib
import json
from typing import Any

import structlog
from redis.asyncio import Redis

from ..models import ProductInfo, CompetitorAnalysis

logger = structlog.get_logger(__name__)


class CacheManager:
    """Manages caching of product info and analysis results with Redis.

    Provides methods to cache and retrieve data with automatic
    expiration and invalidation logic.

    Cache TTLs:
    - Product information: 1 hour (3600 seconds)
    - Analysis results: 24 hours (86400 seconds)

    Requirements: Non-functional requirements - Cost control
    """

    # Cache TTLs in seconds
    PRODUCT_INFO_TTL = 3600  # 1 hour
    ANALYSIS_RESULT_TTL = 86400  # 24 hours
    CREATIVE_SCORE_TTL = 86400  # 24 hours

    # Cache key prefixes
    PREFIX_PRODUCT = "ad_creative:product"
    PREFIX_ANALYSIS = "ad_creative:analysis"
    PREFIX_SCORE = "ad_creative:score"

    def __init__(self, redis_client: Redis | None = None):
        """Initialize cache manager.

        Args:
            redis_client: Redis client instance. If None, caching is disabled.
        """
        self.redis = redis_client
        self._enabled = redis_client is not None

        logger.info(
            "ad_creative_cache_manager_initialized",
            enabled=self._enabled,
            product_ttl=self.PRODUCT_INFO_TTL,
            analysis_ttl=self.ANALYSIS_RESULT_TTL,
        )

    @property
    def enabled(self) -> bool:
        """Check if caching is enabled."""
        return self._enabled

    def _hash_url(self, url: str) -> str:
        """Create a hash of a URL for use as cache key.

        Args:
            url: URL to hash

        Returns:
            MD5 hash of the URL
        """
        return hashlib.md5(url.encode()).hexdigest()

    # =========================================================================
    # Product Information Cache
    # =========================================================================

    async def get_product_info(self, product_url: str) -> ProductInfo | None:
        """Get cached product information.

        Args:
            product_url: Product URL

        Returns:
            Cached ProductInfo if found, None otherwise
        """
        if not self._enabled:
            return None

        cache_key = f"{self.PREFIX_PRODUCT}:{self._hash_url(product_url)}"

        log = logger.bind(
            product_url=product_url[:50],
            cache_key=cache_key,
        )

        try:
            cached_value = await self.redis.get(cache_key)

            if cached_value:
                log.info("product_info_cache_hit")
                data = json.loads(cached_value)
                return ProductInfo(**data)
            else:
                log.debug("product_info_cache_miss")
                return None

        except json.JSONDecodeError as e:
            log.warning("product_info_cache_parse_error", error=str(e))
            await self.redis.delete(cache_key)
            return None

        except Exception as e:
            log.error("product_info_cache_get_error", error=str(e))
            return None

    async def cache_product_info(
        self,
        product_url: str,
        product_info: ProductInfo,
    ) -> bool:
        """Cache product information.

        Args:
            product_url: Product URL
            product_info: Product information to cache

        Returns:
            True if successful, False otherwise
        """
        if not self._enabled:
            return False

        cache_key = f"{self.PREFIX_PRODUCT}:{self._hash_url(product_url)}"

        log = logger.bind(
            product_url=product_url[:50],
            cache_key=cache_key,
            ttl=self.PRODUCT_INFO_TTL,
        )

        try:
            # Serialize to JSON
            json_data = json.dumps(
                product_info.model_dump(mode="json"),
                ensure_ascii=False,
            )

            # Store in Redis with TTL
            result = await self.redis.setex(
                cache_key,
                self.PRODUCT_INFO_TTL,
                json_data,
            )

            if result:
                log.info("product_info_cache_set_success")
                return True
            else:
                log.warning("product_info_cache_set_failed")
                return False

        except (TypeError, ValueError) as e:
            log.error("product_info_cache_serialization_error", error=str(e))
            return False

        except Exception as e:
            log.error("product_info_cache_set_error", error=str(e))
            return False

    # =========================================================================
    # Competitor Analysis Cache
    # =========================================================================

    async def get_competitor_analysis(
        self,
        ad_url: str,
    ) -> CompetitorAnalysis | None:
        """Get cached competitor analysis.

        Args:
            ad_url: Ad URL that was analyzed

        Returns:
            Cached CompetitorAnalysis if found, None otherwise
        """
        if not self._enabled:
            return None

        cache_key = f"{self.PREFIX_ANALYSIS}:{self._hash_url(ad_url)}"

        log = logger.bind(
            ad_url=ad_url[:50],
            cache_key=cache_key,
        )

        try:
            cached_value = await self.redis.get(cache_key)

            if cached_value:
                log.info("competitor_analysis_cache_hit")
                data = json.loads(cached_value)
                return CompetitorAnalysis(**data)
            else:
                log.debug("competitor_analysis_cache_miss")
                return None

        except json.JSONDecodeError as e:
            log.warning("competitor_analysis_cache_parse_error", error=str(e))
            await self.redis.delete(cache_key)
            return None

        except Exception as e:
            log.error("competitor_analysis_cache_get_error", error=str(e))
            return None

    async def cache_competitor_analysis(
        self,
        ad_url: str,
        analysis: CompetitorAnalysis,
    ) -> bool:
        """Cache competitor analysis result.

        Args:
            ad_url: Ad URL that was analyzed
            analysis: Analysis result to cache

        Returns:
            True if successful, False otherwise
        """
        if not self._enabled:
            return False

        cache_key = f"{self.PREFIX_ANALYSIS}:{self._hash_url(ad_url)}"

        log = logger.bind(
            ad_url=ad_url[:50],
            cache_key=cache_key,
            ttl=self.ANALYSIS_RESULT_TTL,
        )

        try:
            # Serialize to JSON
            json_data = json.dumps(
                analysis.model_dump(mode="json"),
                ensure_ascii=False,
            )

            # Store in Redis with TTL
            result = await self.redis.setex(
                cache_key,
                self.ANALYSIS_RESULT_TTL,
                json_data,
            )

            if result:
                log.info("competitor_analysis_cache_set_success")
                return True
            else:
                log.warning("competitor_analysis_cache_set_failed")
                return False

        except (TypeError, ValueError) as e:
            log.error("competitor_analysis_cache_serialization_error", error=str(e))
            return False

        except Exception as e:
            log.error("competitor_analysis_cache_set_error", error=str(e))
            return False

    # =========================================================================
    # Creative Score Cache
    # =========================================================================

    async def get_creative_score(
        self,
        creative_id: str,
    ) -> dict | None:
        """Get cached creative score.

        Args:
            creative_id: Creative ID

        Returns:
            Cached score dict if found, None otherwise
        """
        if not self._enabled:
            return None

        cache_key = f"{self.PREFIX_SCORE}:{creative_id}"

        log = logger.bind(
            creative_id=creative_id,
            cache_key=cache_key,
        )

        try:
            cached_value = await self.redis.get(cache_key)

            if cached_value:
                log.info("creative_score_cache_hit")
                return json.loads(cached_value)
            else:
                log.debug("creative_score_cache_miss")
                return None

        except json.JSONDecodeError as e:
            log.warning("creative_score_cache_parse_error", error=str(e))
            await self.redis.delete(cache_key)
            return None

        except Exception as e:
            log.error("creative_score_cache_get_error", error=str(e))
            return None

    async def cache_creative_score(
        self,
        creative_id: str,
        score_data: dict,
    ) -> bool:
        """Cache creative score.

        Args:
            creative_id: Creative ID
            score_data: Score data to cache

        Returns:
            True if successful, False otherwise
        """
        if not self._enabled:
            return False

        cache_key = f"{self.PREFIX_SCORE}:{creative_id}"

        log = logger.bind(
            creative_id=creative_id,
            cache_key=cache_key,
            ttl=self.CREATIVE_SCORE_TTL,
        )

        try:
            # Serialize to JSON
            json_data = json.dumps(score_data, ensure_ascii=False)

            # Store in Redis with TTL
            result = await self.redis.setex(
                cache_key,
                self.CREATIVE_SCORE_TTL,
                json_data,
            )

            if result:
                log.info("creative_score_cache_set_success")
                return True
            else:
                log.warning("creative_score_cache_set_failed")
                return False

        except (TypeError, ValueError) as e:
            log.error("creative_score_cache_serialization_error", error=str(e))
            return False

        except Exception as e:
            log.error("creative_score_cache_set_error", error=str(e))
            return False

    # =========================================================================
    # Cache Invalidation
    # =========================================================================

    async def invalidate_product_info(self, product_url: str) -> bool:
        """Invalidate cached product information.

        Args:
            product_url: Product URL to invalidate

        Returns:
            True if deleted, False otherwise
        """
        if not self._enabled:
            return False

        cache_key = f"{self.PREFIX_PRODUCT}:{self._hash_url(product_url)}"

        try:
            result = await self.redis.delete(cache_key)
            logger.info(
                "product_info_cache_invalidated",
                product_url=product_url[:50],
                deleted=result > 0,
            )
            return result > 0

        except Exception as e:
            logger.error("product_info_cache_invalidation_error", error=str(e))
            return False

    async def invalidate_competitor_analysis(self, ad_url: str) -> bool:
        """Invalidate cached competitor analysis.

        Args:
            ad_url: Ad URL to invalidate

        Returns:
            True if deleted, False otherwise
        """
        if not self._enabled:
            return False

        cache_key = f"{self.PREFIX_ANALYSIS}:{self._hash_url(ad_url)}"

        try:
            result = await self.redis.delete(cache_key)
            logger.info(
                "competitor_analysis_cache_invalidated",
                ad_url=ad_url[:50],
                deleted=result > 0,
            )
            return result > 0

        except Exception as e:
            logger.error("competitor_analysis_cache_invalidation_error", error=str(e))
            return False

    async def invalidate_creative_score(self, creative_id: str) -> bool:
        """Invalidate cached creative score.

        Args:
            creative_id: Creative ID to invalidate

        Returns:
            True if deleted, False otherwise
        """
        if not self._enabled:
            return False

        cache_key = f"{self.PREFIX_SCORE}:{creative_id}"

        try:
            result = await self.redis.delete(cache_key)
            logger.info(
                "creative_score_cache_invalidated",
                creative_id=creative_id,
                deleted=result > 0,
            )
            return result > 0

        except Exception as e:
            logger.error("creative_score_cache_invalidation_error", error=str(e))
            return False

    async def invalidate_all_user_cache(self, user_id: str) -> int:
        """Invalidate all cache entries for a user.

        Note: This requires user_id to be part of the cache key,
        which is not currently implemented. This method is a placeholder
        for future implementation.

        Args:
            user_id: User ID

        Returns:
            Number of entries deleted
        """
        logger.warning(
            "invalidate_all_user_cache_not_implemented",
            user_id=user_id,
        )
        return 0
