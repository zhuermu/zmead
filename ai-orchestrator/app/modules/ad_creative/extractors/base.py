"""
Base extractor class for product information extraction.

Defines the abstract interface for all product information extractors.
Each platform-specific extractor (Shopify, Amazon, etc.) must implement
the extract() and supports() methods.

Requirements: 1.1
"""

import re
from abc import ABC, abstractmethod
from typing import ClassVar

import structlog

from ..models import ProductInfo

logger = structlog.get_logger(__name__)


class ExtractionError(Exception):
    """Exception raised when product extraction fails.

    Attributes:
        message: Human-readable error description
        error_code: Machine-readable error code
        url: The URL that failed extraction
        recoverable: Whether the error might be resolved by retry
    """

    def __init__(
        self,
        message: str,
        error_code: str = "6007",
        url: str | None = None,
        recoverable: bool = False,
    ):
        self.message = message
        self.error_code = error_code
        self.url = url
        self.recoverable = recoverable
        super().__init__(self.message)


class InvalidURLError(ExtractionError):
    """Exception raised when the URL format is invalid."""

    def __init__(self, url: str, reason: str = "Invalid URL format"):
        super().__init__(
            message=f"{reason}: {url}",
            error_code="6006",
            url=url,
            recoverable=False,
        )


class BaseExtractor(ABC):
    """Base class for product information extractors.

    All platform-specific extractors should inherit from this class
    and implement the extract() and supports() methods.

    Attributes:
        PLATFORM_NAME: Name of the platform this extractor handles
        URL_PATTERNS: List of regex patterns to match supported URLs
    """

    PLATFORM_NAME: ClassVar[str] = "unknown"
    URL_PATTERNS: ClassVar[list[str]] = []

    def __init__(self):
        """Initialize the extractor."""
        self._log = logger.bind(extractor=self.__class__.__name__)

    @abstractmethod
    async def extract(self, product_url: str) -> ProductInfo:
        """Extract product information from URL.

        This method must be implemented by all subclasses to handle
        platform-specific extraction logic.

        Args:
            product_url: URL of the product page

        Returns:
            ProductInfo with extracted data including:
            - title: Product title
            - price: Product price
            - currency: Currency code (e.g., "USD")
            - images: List of product image URLs
            - description: Product description
            - selling_points: List of key selling points
            - source: Platform identifier

        Raises:
            InvalidURLError: If the URL format is invalid
            ExtractionError: If extraction fails for other reasons
        """
        pass

    @abstractmethod
    def supports(self, url: str) -> bool:
        """Check if this extractor supports the given URL.

        Args:
            url: URL to check

        Returns:
            True if this extractor can handle the URL
        """
        pass

    def validate_url(self, url: str) -> bool:
        """Validate that the URL is well-formed.

        Args:
            url: URL to validate

        Returns:
            True if URL is valid

        Raises:
            InvalidURLError: If URL is malformed
        """
        if not url:
            raise InvalidURLError(url or "", "URL cannot be empty")

        # Basic URL pattern check
        url_pattern = re.compile(
            r"^https?://"  # http:// or https://
            r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+"  # domain
            r"(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|"  # TLD
            r"localhost|"  # localhost
            r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # or IP
            r"(?::\d+)?"  # optional port
            r"(?:/?|[/?]\S+)$",
            re.IGNORECASE,
        )

        if not url_pattern.match(url):
            raise InvalidURLError(url, "URL format is invalid")

        return True

    def _extract_selling_points(self, text: str, max_points: int = 5) -> list[str]:
        """Extract selling points from product description.

        Looks for bullet points, numbered lists, or key phrases.

        Args:
            text: Product description text
            max_points: Maximum number of selling points to extract

        Returns:
            List of selling point strings
        """
        if not text:
            return []

        selling_points = []

        # Look for bullet points (•, -, *, ✓, ✔)
        bullet_pattern = re.compile(r"[•\-\*✓✔]\s*(.+?)(?=\n|$)")
        bullets = bullet_pattern.findall(text)
        selling_points.extend([b.strip() for b in bullets if len(b.strip()) > 10])

        # Look for numbered lists
        numbered_pattern = re.compile(r"\d+[.)]\s*(.+?)(?=\n|$)")
        numbered = numbered_pattern.findall(text)
        selling_points.extend([n.strip() for n in numbered if len(n.strip()) > 10])

        # Remove duplicates while preserving order
        seen = set()
        unique_points = []
        for point in selling_points:
            if point.lower() not in seen:
                seen.add(point.lower())
                unique_points.append(point)

        return unique_points[:max_points]

    def _clean_price(self, price_str: str) -> tuple[float, str]:
        """Parse price string into numeric value and currency.

        Args:
            price_str: Price string (e.g., "$29.99", "€19.99", "¥199")

        Returns:
            Tuple of (price_value, currency_code)
        """
        if not price_str:
            return 0.0, "USD"

        # Currency symbol to code mapping
        currency_map = {
            "$": "USD",
            "€": "EUR",
            "£": "GBP",
            "¥": "CNY",
            "₹": "INR",
            "A$": "AUD",
            "C$": "CAD",
        }

        # Detect currency
        currency = "USD"
        for symbol, code in currency_map.items():
            if symbol in price_str:
                currency = code
                break

        # Extract numeric value
        price_pattern = re.compile(r"[\d,]+\.?\d*")
        match = price_pattern.search(price_str.replace(",", ""))
        if match:
            try:
                price = float(match.group())
                return price, currency
            except ValueError:
                pass

        return 0.0, currency

    def _clean_html(self, html: str) -> str:
        """Remove HTML tags from text.

        Args:
            html: HTML string

        Returns:
            Plain text with HTML tags removed
        """
        if not html:
            return ""

        # Remove script and style elements
        html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL)
        html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL)

        # Remove HTML tags
        html = re.sub(r"<[^>]+>", " ", html)

        # Clean up whitespace
        html = re.sub(r"\s+", " ", html)

        return html.strip()
