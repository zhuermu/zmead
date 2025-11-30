"""
Base extractor interface for product information extraction.

Provides abstract base class for platform-specific extractors.

Requirements: 1.1
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..models import ProductInfo


class ExtractorError(Exception):
    """Base exception for extractor errors"""

    def __init__(self, message: str, code: str | None = None):
        self.message = message
        self.code = code
        super().__init__(message)


class BaseExtractor(ABC):
    """产品信息提取器基类

    Abstract base class for platform-specific product extractors.
    Subclasses must implement extract() and supports() methods.

    Requirements: 1.1
    """

    # Platform name identifier - must be set by subclasses
    PLATFORM_NAME: str = "unknown"

    @abstractmethod
    async def extract(self, product_url: str) -> "ProductInfo":
        """提取产品信息

        Args:
            product_url: Product URL to extract information from

        Returns:
            ProductInfo with extracted product data

        Raises:
            ExtractorError: If extraction fails
        """
        pass

    @abstractmethod
    def supports(self, url: str) -> bool:
        """检查是否支持该 URL

        Args:
            url: URL to check

        Returns:
            True if this extractor supports the URL
        """
        pass
