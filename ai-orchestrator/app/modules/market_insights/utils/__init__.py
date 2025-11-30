"""Utility modules for Market Insights."""

from app.modules.market_insights.utils.cache_manager import CacheManager
from app.modules.market_insights.utils.degradation_handler import DegradationHandler
from app.modules.market_insights.utils.error_handler import (
    CampaignDataError,
    CompetitorAnalysisError,
    ErrorResponseFormatter,
    InvalidURLError,
    MarketInsightsErrorHandler,
    PyTrendsError,
    PyTrendsRateLimitError,
    PyTrendsTimeoutError,
    StrategyNotFoundError,
    StrategyTrackingError,
    ThirdPartyAPIError,
    TikTokAPIError,
    TikTokAuthError,
    TikTokRateLimitError,
    TikTokServiceError,
    URLAccessError,
)
from app.modules.market_insights.utils.rate_limiter import RateLimiter, RateLimiterRegistry
from app.modules.market_insights.utils.retry_strategy import (
    APIError,
    RateLimitError,
    RetryableError,
    RetryStrategy,
    TimeoutConfig,
    TimeoutError,
    retry_with_backoff,
)

__all__ = [
    "CacheManager",
    "DegradationHandler",
    "RateLimiter",
    "RateLimiterRegistry",
    "retry_with_backoff",
    "RetryStrategy",
    "TimeoutConfig",
    "RetryableError",
    "TimeoutError",
    "RateLimitError",
    "APIError",
    "MarketInsightsErrorHandler",
    "ErrorResponseFormatter",
    "ThirdPartyAPIError",
    "TikTokAPIError",
    "TikTokAuthError",
    "TikTokRateLimitError",
    "TikTokServiceError",
    "PyTrendsError",
    "PyTrendsRateLimitError",
    "PyTrendsTimeoutError",
    "CompetitorAnalysisError",
    "InvalidURLError",
    "URLAccessError",
    "StrategyTrackingError",
    "StrategyNotFoundError",
    "CampaignDataError",
]
