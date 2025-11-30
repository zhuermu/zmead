"""
Product information extractors for Landing Page module.

Provides extractors for different e-commerce platforms:
- ShopifyExtractor: Extracts product info from Shopify stores
- AmazonExtractor: Extracts product info from Amazon listings
- ExtractorRouter: Auto-selects correct extractor based on URL

Requirements: 1.1, 1.2, 1.3, 1.5
"""

from .base import BaseExtractor, ExtractorError
from .shopify_extractor import ShopifyExtractor
from .amazon_extractor import AmazonExtractor
from .router import ExtractorRouter, UnsupportedURLError, get_extractor_router

__all__ = [
    "BaseExtractor",
    "ExtractorError",
    "ShopifyExtractor",
    "AmazonExtractor",
    "ExtractorRouter",
    "UnsupportedURLError",
    "get_extractor_router",
]
