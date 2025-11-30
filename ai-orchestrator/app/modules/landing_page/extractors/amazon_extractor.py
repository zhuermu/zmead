"""
Amazon product information extractor for Landing Page module.

Extracts product information from Amazon product pages using web scraping.
Supports multiple Amazon domains (US, UK, DE, JP, CN, etc.).

Requirements: 1.3
"""

import re
from urllib.parse import urlparse

import aiohttp
import structlog
from bs4 import BeautifulSoup

from ..models import ProductInfo, Review
from .base import BaseExtractor, ExtractorError

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

    Requirements: 1.3
    """

    PLATFORM_NAME = "amazon"

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
            ExtractorError: If extraction fails
        """
        logger.info("amazon_extraction_start", url=product_url)

        # Detect currency from domain
        currency = self._detect_currency(product_url)

        try:
            # Fetch product page HTML
            html = await self._fetch_page(product_url)

            # Parse HTML
            soup = BeautifulSoup(html, "html.parser")

            # Extract product information
            product_info = self._parse_product_page(soup, currency)

            logger.info(
                "amazon_extraction_success",
                title=product_info.title,
                price=product_info.price,
                image_count=len(product_info.images),
            )

            return product_info

        except aiohttp.ClientError as e:
            logger.error("amazon_network_error", error=str(e))
            raise ExtractorError(
                message=f"Failed to fetch Amazon product: {str(e)}",
                code="6007",
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
            ExtractorError: If page cannot be fetched
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
                    raise ExtractorError(
                        message="Product not found",
                        code="6007",
                    )

                if response.status != 200:
                    raise ExtractorError(
                        message=f"Amazon returned status {response.status}",
                        code="6007",
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
        main_image = images[0] if images else "https://placeholder.com/product.jpg"

        # Extract description
        description = self._extract_description(soup)

        # Extract features (bullet points)
        features = self._extract_bullet_points(soup)

        # Extract reviews
        reviews = self._extract_reviews(soup)

        return ProductInfo(
            title=title,
            price=price,
            currency=currency,
            main_image=main_image,
            images=images,
            description=description[:2000] if description else "",
            features=features[:5],
            reviews=reviews[:3],
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
                price = self._clean_price(price_text)
                if price > 0:
                    return price

        return 0.0

    def _clean_price(self, price_text: str) -> float:
        """Clean price text and convert to float.

        Args:
            price_text: Raw price text (e.g., "$99.99", "€49,99")

        Returns:
            Price as float
        """
        if not price_text:
            return 0.0

        # Remove currency symbols and whitespace
        cleaned = re.sub(r"[^\d.,]", "", price_text)

        # Handle European format (1.234,56 -> 1234.56)
        if "," in cleaned and "." in cleaned:
            if cleaned.index(",") > cleaned.index("."):
                cleaned = cleaned.replace(".", "").replace(",", ".")
            else:
                cleaned = cleaned.replace(",", "")
        elif "," in cleaned:
            # Could be decimal separator or thousands
            parts = cleaned.split(",")
            if len(parts) == 2 and len(parts[1]) == 2:
                cleaned = cleaned.replace(",", ".")
            else:
                cleaned = cleaned.replace(",", "")

        try:
            return float(cleaned)
        except ValueError:
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

    def _clean_html(self, html: str) -> str:
        """Remove HTML tags and clean up text.

        Args:
            html: HTML string

        Returns:
            Clean text
        """
        if not html:
            return ""

        # Remove HTML tags
        text = re.sub(r"<[^>]+>", " ", html)
        # Normalize whitespace
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def _extract_bullet_points(self, soup: BeautifulSoup) -> list[str]:
        """Extract feature bullet points from page.

        Args:
            soup: BeautifulSoup parsed HTML

        Returns:
            List of features
        """
        features = []

        # Find feature bullets
        bullets = soup.select("#feature-bullets li")
        for bullet in bullets:
            text = bullet.get_text(strip=True)
            # Filter out empty or very short bullets
            if text and len(text) > 10:
                # Remove "About this item" header if present
                if not text.lower().startswith("about this"):
                    features.append(text)

        # Also try product details section
        if not features:
            details = soup.select(".a-unordered-list li")
            for detail in details[:10]:
                text = detail.get_text(strip=True)
                if text and len(text) > 10 and len(text) < 200:
                    features.append(text)

        return features[:5]

    def _extract_reviews(self, soup: BeautifulSoup) -> list[Review]:
        """Extract product reviews from page.

        Args:
            soup: BeautifulSoup parsed HTML

        Returns:
            List of Review objects
        """
        reviews = []

        # Find review elements
        review_elements = soup.select(".review")
        for review_el in review_elements[:3]:
            # Extract rating
            rating_el = review_el.select_one(".review-rating")
            rating = 5  # Default
            if rating_el:
                rating_text = rating_el.get_text(strip=True)
                match = re.search(r"(\d)", rating_text)
                if match:
                    rating = int(match.group(1))

            # Extract review text
            text_el = review_el.select_one(".review-text")
            text = ""
            if text_el:
                text = text_el.get_text(strip=True)[:500]

            if text:
                reviews.append(Review(rating=rating, text=text))

        return reviews
