"""
Shopify product information extractor for Landing Page module.

Extracts product information from Shopify stores using the Storefront API
or by parsing the product JSON endpoint.

Requirements: 1.2, 1.5
"""

import re
from urllib.parse import urlparse

import aiohttp
import structlog

from ..models import ProductInfo, Review
from .base import BaseExtractor, ExtractorError
from ..utils import with_retry

logger = structlog.get_logger(__name__)


class ShopifyExtractor(BaseExtractor):
    """Extracts product information from Shopify stores.

    Uses Shopify's public product JSON endpoint to extract product data.
    This approach works for most Shopify stores without requiring API keys.

    Supported URL formats:
    - https://store.myshopify.com/products/product-handle
    - https://custom-domain.com/products/product-handle
    - https://store.myshopify.com/collections/*/products/product-handle

    Requirements: 1.2
    """

    PLATFORM_NAME = "shopify"

    # Request timeout in seconds
    REQUEST_TIMEOUT = 30

    # User agent for requests
    USER_AGENT = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )

    def supports(self, url: str) -> bool:
        """Check if URL is a Shopify store.

        Detects Shopify stores by:
        1. .myshopify.com domain
        2. /products/ path pattern (common Shopify URL structure)

        Args:
            url: URL to check

        Returns:
            True if this appears to be a Shopify product URL
        """
        if not url:
            return False

        url_lower = url.lower()

        # Direct myshopify.com domain
        if ".myshopify.com" in url_lower:
            return True

        # Check for /products/ path (common Shopify pattern)
        # Note: This may match non-Shopify sites, but we'll verify during extraction
        if "/products/" in url_lower:
            return True

        return False

    async def extract(self, product_url: str) -> ProductInfo:
        """Extract product information from Shopify URL.

        Uses the .json endpoint that Shopify provides for product pages.
        For example: /products/product-handle.json

        Args:
            product_url: Shopify product URL

        Returns:
            ProductInfo with extracted data

        Raises:
            ExtractorError: If extraction fails
        """
        logger.info("shopify_extraction_start", url=product_url)

        # Parse URL and construct JSON endpoint
        json_url = self._get_json_url(product_url)
        logger.debug("shopify_json_url", json_url=json_url)

        try:
            # Fetch product JSON
            product_data = await self._fetch_product_json(json_url)

            # Parse product data
            product_info = self._parse_product_data(product_data)

            logger.info(
                "shopify_extraction_success",
                title=product_info.title,
                price=product_info.price,
                image_count=len(product_info.images),
            )

            return product_info

        except aiohttp.ClientError as e:
            logger.error("shopify_network_error", error=str(e))
            raise ExtractorError(
                message=f"Failed to fetch Shopify product: {str(e)}",
                code="6007",
            )
        except KeyError as e:
            logger.error("shopify_parse_error", error=str(e))
            raise ExtractorError(
                message=f"Failed to parse Shopify product data: missing {str(e)}",
                code="6007",
            )

    def _get_json_url(self, product_url: str) -> str:
        """Convert product URL to JSON endpoint URL.

        Args:
            product_url: Original product URL

        Returns:
            URL to the product JSON endpoint

        Raises:
            ExtractorError: If URL cannot be parsed
        """
        parsed = urlparse(product_url)

        # Extract the product path
        path = parsed.path

        # Handle collection URLs: /collections/*/products/handle
        collection_match = re.search(r"/products/([a-zA-Z0-9\-_]+)", path)
        if collection_match:
            product_handle = collection_match.group(1)
            # Remove any query params or fragments from handle
            product_handle = product_handle.split("?")[0].split("#")[0]
            json_path = f"/products/{product_handle}.json"
        else:
            raise ExtractorError(
                message="Could not extract product handle from URL",
                code="6006",
            )

        # Reconstruct URL with JSON endpoint
        return f"{parsed.scheme}://{parsed.netloc}{json_path}"

    @with_retry(
        max_retries=3,
        base_delay=2.0,
        retryable_exceptions=(
            aiohttp.ClientError,
            aiohttp.ServerTimeoutError,
            TimeoutError,
        )
    )
    async def _fetch_product_json(self, json_url: str) -> dict:
        """Fetch product data from Shopify JSON endpoint.

        This method includes automatic retry logic for transient network errors.

        Args:
            json_url: URL to the product JSON endpoint

        Returns:
            Product data dictionary

        Raises:
            aiohttp.ClientError: On network errors (after retries)
            ExtractorError: If response is not valid JSON or product not found
        """
        headers = {
            "User-Agent": self.USER_AGENT,
            "Accept": "application/json",
        }

        timeout = aiohttp.ClientTimeout(total=self.REQUEST_TIMEOUT)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(json_url, headers=headers) as response:
                if response.status == 404:
                    raise ExtractorError(
                        message="Product not found",
                        code="6007",
                    )

                if response.status != 200:
                    raise ExtractorError(
                        message=f"Shopify returned status {response.status}",
                        code="6007",
                    )

                try:
                    data = await response.json()
                except Exception as e:
                    raise ExtractorError(
                        message=f"Invalid JSON response: {str(e)}",
                        code="6007",
                    )

                return data

    def _parse_product_data(self, data: dict) -> ProductInfo:
        """Parse Shopify product JSON into ProductInfo.

        Args:
            data: Raw product JSON from Shopify

        Returns:
            ProductInfo with parsed data
        """
        product = data.get("product", data)

        # Extract title
        title = product.get("title", "")

        # Extract price from first variant
        variants = product.get("variants", [])
        price = 0.0
        currency = "USD"
        if variants:
            price_str = variants[0].get("price", "0")
            try:
                price = float(price_str)
            except (ValueError, TypeError):
                price = 0.0

        # Extract images
        images = []
        for img in product.get("images", []):
            src = img.get("src", "")
            if src:
                # Remove size parameters to get full resolution
                src = re.sub(r"_\d+x\d*\.", ".", src)
                images.append(src)

        # Get main image
        main_image = images[0] if images else "https://placeholder.com/product.jpg"

        # Extract description (HTML)
        description_html = product.get("body_html", "")
        description = self._clean_html(description_html)

        # Extract features from description and tags
        features = self._extract_features(description)

        # Add tags as potential features
        tags = product.get("tags", [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",")]

        # Filter meaningful tags (not internal tags)
        meaningful_tags = [
            tag for tag in tags if len(tag) > 3 and not tag.startswith("_")
        ]
        features.extend(meaningful_tags[:3])

        # Deduplicate features
        seen = set()
        unique_features = []
        for feature in features:
            if feature.lower() not in seen:
                seen.add(feature.lower())
                unique_features.append(feature)

        return ProductInfo(
            title=title,
            price=price,
            currency=currency,
            main_image=main_image,
            images=images,
            description=description[:2000] if description else "",
            features=unique_features[:5],
            reviews=[],  # Shopify API doesn't provide reviews directly
            source="shopify",
        )

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

    def _extract_features(self, description: str) -> list[str]:
        """Extract feature bullet points from description.

        Args:
            description: Product description text

        Returns:
            List of features
        """
        features = []

        # Split by common separators
        lines = re.split(r"[•\-\*\n]", description)

        for line in lines:
            line = line.strip()
            # Filter meaningful lines
            if len(line) > 10 and len(line) < 200:
                features.append(line)

        return features[:5]
