"""
Product information extractors for various e-commerce platforms.

This module provides extractors for:
- Shopify stores (via Storefront API)
- Amazon product pages (via web scraping)

Usage:
    from app.modules.ad_creative.extractors import get_extractor

    extractor = get_extractor(product_url)
    if extractor:
        product_info = await extractor.extract(product_url)
"""

from .amazon_extractor import AmazonExtractor
from .base import BaseExtractor, ExtractionError, InvalidURLError
from .shopify_extractor import ShopifyExtractor

# Registry of all available extractors
_EXTRACTORS: list[type[BaseExtractor]] = [
    ShopifyExtractor,
    AmazonExtractor,
]


def get_extractor(url: str) -> BaseExtractor | None:
    """Get the appropriate extractor for a given URL.

    Args:
        url: Product URL to find extractor for

    Returns:
        Extractor instance if one supports the URL, None otherwise
    """
    for extractor_class in _EXTRACTORS:
        extractor = extractor_class()
        if extractor.supports(url):
            return extractor
    return None


def get_supported_platforms() -> list[str]:
    """Get list of supported platform names.

    Returns:
        List of platform names (e.g., ["shopify", "amazon"])
    """
    return [cls.PLATFORM_NAME for cls in _EXTRACTORS]


__all__ = [
    "BaseExtractor",
    "ExtractionError",
    "InvalidURLError",
    "ShopifyExtractor",
    "AmazonExtractor",
    "get_extractor",
    "get_supported_platforms",
]
