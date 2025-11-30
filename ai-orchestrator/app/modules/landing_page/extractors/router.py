"""
Extractor router for Landing Page module.

Auto-selects the correct extractor based on URL pattern and handles
unsupported URLs with appropriate errors.

Requirements: 1.2, 1.3, 1.5
"""

import structlog

from ..models import ProductInfo
from .base import BaseExtractor, ExtractorError
from .shopify_extractor import ShopifyExtractor
from .amazon_extractor import AmazonExtractor

logger = structlog.get_logger(__name__)


class UnsupportedURLError(ExtractorError):
    """Error raised when URL is not supported by any extractor."""

    def __init__(self, url: str):
        self.url = url
        super().__init__(
            message=f"Unsupported URL: {url}. Supported platforms: Shopify, Amazon",
            code="6006",
        )


class ExtractorRouter:
    """Routes product URLs to the appropriate extractor.

    Auto-selects the correct extractor based on URL pattern.
    Supports Shopify and Amazon platforms.

    Requirements: 1.2, 1.3, 1.5
    """

    def __init__(self):
        """Initialize router with available extractors."""
        self._extractors: list[BaseExtractor] = [
            ShopifyExtractor(),
            AmazonExtractor(),
        ]
        logger.info(
            "extractor_router_initialized",
            extractors=[e.__class__.__name__ for e in self._extractors],
        )

    def get_extractor(self, url: str) -> BaseExtractor:
        """Get the appropriate extractor for a URL.

        Args:
            url: Product URL to find extractor for

        Returns:
            BaseExtractor that supports the URL

        Raises:
            UnsupportedURLError: If no extractor supports the URL
        """
        if not url:
            raise UnsupportedURLError("")

        for extractor in self._extractors:
            if extractor.supports(url):
                logger.debug(
                    "extractor_selected",
                    url=url,
                    extractor=extractor.__class__.__name__,
                )
                return extractor

        logger.warning("no_extractor_found", url=url)
        raise UnsupportedURLError(url)

    def supports(self, url: str) -> bool:
        """Check if any extractor supports the URL.

        Args:
            url: URL to check

        Returns:
            True if any extractor supports the URL
        """
        if not url:
            return False

        for extractor in self._extractors:
            if extractor.supports(url):
                return True

        return False

    def detect_platform(self, url: str) -> str | None:
        """Detect the platform for a URL.

        Args:
            url: URL to detect platform for

        Returns:
            Platform name (e.g., "shopify", "amazon") or None if unsupported
        """
        if not url:
            return None

        for extractor in self._extractors:
            if extractor.supports(url):
                return extractor.PLATFORM_NAME

        return None

    async def extract(self, url: str) -> ProductInfo:
        """Extract product information from URL.

        Auto-selects the correct extractor and extracts product info.

        Args:
            url: Product URL to extract from

        Returns:
            ProductInfo with extracted data

        Raises:
            UnsupportedURLError: If no extractor supports the URL
            ExtractorError: If extraction fails
        """
        extractor = self.get_extractor(url)

        logger.info(
            "extraction_start",
            url=url,
            extractor=extractor.__class__.__name__,
        )

        try:
            product_info = await extractor.extract(url)
            logger.info(
                "extraction_success",
                url=url,
                title=product_info.title,
                platform=product_info.source,
            )
            return product_info
        except ExtractorError:
            # Re-raise extractor errors as-is
            raise
        except Exception as e:
            # Wrap unexpected errors
            logger.error("extraction_unexpected_error", url=url, error=str(e))
            raise ExtractorError(
                message=f"Unexpected error during extraction: {str(e)}",
                code="6007",
            )

    @property
    def supported_platforms(self) -> list[str]:
        """Get list of supported platform names.

        Returns:
            List of platform names
        """
        return [e.PLATFORM_NAME for e in self._extractors]


# Singleton instance for convenience
_router_instance: ExtractorRouter | None = None


def get_extractor_router() -> ExtractorRouter:
    """Get the singleton ExtractorRouter instance.

    Returns:
        ExtractorRouter instance
    """
    global _router_instance
    if _router_instance is None:
        _router_instance = ExtractorRouter()
    return _router_instance
