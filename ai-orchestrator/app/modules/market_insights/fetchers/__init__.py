"""
Data fetchers for TikTok Creative Center and Google Trends APIs.
"""

from .tiktok_fetcher import TikTokFetcher
from .trends_fetcher import TrendsFetcher

__all__ = [
    "TikTokFetcher",
    "TrendsFetcher",
]
