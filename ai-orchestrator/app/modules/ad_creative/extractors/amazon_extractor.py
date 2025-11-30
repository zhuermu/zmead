"""
Amazon product information extractor.

Extracts product information from Amazon product pages using web scraping.
Supports multiple Amazon domains (US, UK, DE, JP, CN, etc.).

Requirements: 1.4
"""

import re
from urllib.parse import urlparse

import aiohttp
import structlog
from bs4 import BeautifulSoup

from ..models import ProductInfo
from .base import BaseExtractor, ExtractionError

logger = structlog.get_logger(__name__)


class AmazonExtractor(BaseExtractor):
    """Extracts product information from Amazon product pages.

    Uses web scraping with BeautifulSoup to parse Amazon product pages.
    Handles various Amazon page layouts and regional domains.

    Supported domains:
    - amazon.com (US)
    - amazon.co.uk (UK)
    - amazon.de (Germany)
    - amazon.fr (France)
    - amazon.co.jp (Japan)
    - amazon.cn (China)
    - amazon.ca (Canada)
    - amazon.com.au (Australia)

    Requirements: 1.4
    """

    PLATFORM_NAME = "amazon"
    URL_PATTERNS = [
        r"amazon\.(com|co\.uk|de|fr|co\.jp|cn|ca|com\.au)",
    ]

    # Supported Amazon domains with their currency
    DOMAIN_CURRENCY = {
        "amazon.com": "USD",
        "amazon.co.uk": "GBP",
        "amazon.de": "EUR",
        "amazon.fr": "EUR",
        "amazon.co.jp": "JPY",
        "amazon.cn": "CNY",
        "amazon.ca": "CAD",
        "amazon.com.au": "AUD",
    }

    # Request timeout in seconds
    REQUEST_TIMEOUT = 30

    # User agent to mimic browser
    USER_AGENT = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )

    def supports(self, url: str) -> bool:
        """Check if URL is an Amazon product page.

        Args:
            url: URL to check

        Returns:
            True if this is an Amazon product URL
        """
        if not url:
            return False

        url_lower = url.lower()

        # Check for Amazon domains
        for domain in self.DOMAIN_CURRENCY.keys():
            if domain in url_lower:
                return True

        return False

    async def extract(self, product_url: str) -> ProductInfo:
        """Extract product information from Amazon URL.

        Fetches the product page and parses it using BeautifulSoup
        to extract product details.

        Args:
            product_url: Amazon product URL

        Returns:
            ProductInfo with extracted data

        Raises:
            InvalidURLError: If URL format is invalid
            ExtractionError: If extraction fails
        """
        log = self._log.bind(url=product_url)
        log.info("amazon_extraction_start")

        # Validate URL format
        self.validate_url(product_url)

        # Detect currency from domain
        currency = self._detect_currency(product_url)

        try:
            # Fetch product page HTML
            html = await self._fetch_page(product_url)

            # Parse HTML
            soup = BeautifulSoup(html, "html.parser")

            # Extract product information
            product_info = self._parse_product_page(soup, currency)

            log.info(
                "amazon_extraction_success",
                title=product_info.title,
                price=product_info.price,
                image_count=len(product_info.images),
            )

            return product_info

        except aiohttp.ClientError as e:
            log.error("amazon_network_error", error=str(e))
            raise ExtractionError(
                message=f"Failed to fetch Amazon product: {str(e)}",
                error_code="6007",
                url=product_url,
                recoverable=True,
            )

    def _detect_currency(self, url: str) -> str:
        """Detect currency based on Amazon domain.

        Args:
            url: Amazon URL

        Returns:
            Currency code (e.g., "USD", "GBP")
        """
        parsed = urlparse(url)
        host = parsed.netloc.lower()

        for domain, currency in self.DOMAIN_CURRENCY.items():
            if domain in host:
                return currency

        return "USD"  # Default to USD

    async def _fetch_page(self, url: str) -> str:
        """Fetch Amazon product page HTML.

        Args:
            url: Product page URL

        Returns:
            HTML content as string

        Raises:
            aiohttp.ClientError: On network errors
            ExtractionError: If page cannot be fetched
        """
        headers = {
            "User-Agent": self.USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

        timeout = aiohttp.ClientTimeout(total=self.REQUEST_TIMEOUT)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 404:
                    raise ExtractionError(
                        message="Product not found",
                        error_code="6007",
                        url=url,
                        recoverable=False,
                    )

                if response.status != 200:
                    raise ExtractionError(
                        message=f"Amazon returned status {response.status}",
                        error_code="6007",
                        url=url,
                        recoverable=response.status >= 500,
                    )

                return await response.text()

    def _parse_product_page(self, soup: BeautifulSoup, currency: str) -> ProductInfo:
        """Parse Amazon product page HTML.

        Args:
            soup: BeautifulSoup parsed HTML
            currency: Currency code for this Amazon domain

        Returns:
            ProductInfo with parsed data
        """
        # Extract title
        title = self._extract_title(soup)

        # Extract price
        price = self._extract_price(soup)

        # Extract images
        images = self._extract_images(soup)

        # Extract description
        description = self._extract_description(soup)

        # Extract selling points (bullet points)
        selling_points = self._extract_bullet_points(soup)

        return ProductInfo(
            title=title,
            price=price,
            currency=currency,
            images=images,
            description=description[:2000] if description else "",
            selling_points=selling_points[:5],
            source="amazon",
        )

    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract product title from page.

        Args:
            soup: BeautifulSoup parsed HTML

        Returns:
            Product title
        """
        # Try multiple selectors for title
        selectors = [
            "#productTitle",
            "#title",
            "h1.product-title-word-break",
            "h1[data-automation-id='title']",
        ]

        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                return element.get_text(strip=True)

        return ""

    def _extract_price(self, soup: BeautifulSoup) -> float:
        """Extract product price from page.

        Args:
            soup: BeautifulSoup parsed HTML

        Returns:
            Price as float
        """
        # Try multiple selectors for price
        selectors = [
            ".a-price .a-offscreen",
            "#priceblock_ourprice",
            "#priceblock_dealprice",
            "#priceblock_saleprice",
            ".a-price-whole",
            "#corePrice_feature_div .a-offscreen",
            "#corePriceDisplay_desktop_feature_div .a-offscreen",
        ]

        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                price_text = element.get_text(strip=True)
                price, _ = self._clean_price(price_text)
                if price > 0:
                    return price

        return 0.0

    def _extract_images(self, soup: BeautifulSoup) -> list[str]:
        """Extract product images from page.

        Args:
            soup: BeautifulSoup parsed HTML

        Returns:
            List of image URLs
        """
        images = []

        # Try to find main image
        main_image = soup.select_one("#landingImage")
        if main_image:
            # Get high-res image from data attribute
            src = main_image.get("data-old-hires") or main_image.get("src")
            if src:
                images.append(src)

        # Try to find thumbnail images
        thumbnails = soup.select("#altImages img")
        for thumb in thumbnails:
            src = thumb.get("src", "")
            if src and "sprite" not in src.lower():
                # Convert thumbnail URL to full-size
                full_src = re.sub(r"\._[A-Z0-9_]+_\.", ".", src)
                if full_src not in images:
                    images.append(full_src)

        # Also try image gallery
        gallery_images = soup.select(".imgTagWrapper img")
        for img in gallery_images:
            src = img.get("data-old-hires") or img.get("src")
            if src and src not in images:
                images.append(src)

        return images[:10]  # Limit to 10 images

    def _extract_description(self, soup: BeautifulSoup) -> str:
        """Extract product description from page.

        Args:
            soup: BeautifulSoup parsed HTML

        Returns:
            Product description text
        """
        # Try multiple selectors for description
        selectors = [
            "#productDescription",
            "#feature-bullets",
            "#aplus-content",
            ".a-expander-content",
        ]

        descriptions = []
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                text = self._clean_html(str(element))
                if text:
                    descriptions.append(text)

        return " ".join(descriptions)

    def _extract_bullet_points(self, soup: BeautifulSoup) -> list[str]:
        """Extract feature bullet points from page.

        Args:
            soup: BeautifulSoup parsed HTML

        Returns:
            List of selling points
        """
        selling_points = []

        # Find feature bullets
        bullets = soup.select("#feature-bullets li")
        for bullet in bullets:
            text = bullet.get_text(strip=True)
            # Filter out empty or very short bullets
            if text and len(text) > 10:
                # Remove "About this item" header if present
                if not text.lower().startswith("about this"):
                    selling_points.append(text)

        # Also try product details section
        if not selling_points:
            details = soup.select(".a-unordered-list li")
            for detail in details[:10]:
                text = detail.get_text(strip=True)
                if text and len(text) > 10 and len(text) < 200:
                    selling_points.append(text)

        return selling_points[:5]
