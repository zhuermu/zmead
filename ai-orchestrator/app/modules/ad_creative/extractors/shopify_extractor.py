"""
Shopify product information extractor.

Extracts product information from Shopify stores using the Storefront API
or by parsing the product JSON endpoint.

Requirements: 1.3
"""

import re
from urllib.parse import urlparse

import aiohttp
import structlog

from ..models import ProductInfo
from .base import BaseExtractor, ExtractionError, InvalidURLError

logger = structlog.get_logger(__name__)


class ShopifyExtractor(BaseExtractor):
    """Extracts product information from Shopify stores.

    Uses Shopify's public product JSON endpoint to extract product data.
    This approach works for most Shopify stores without requiring API keys.

    Supported URL formats:
    - https://store.myshopify.com/products/product-handle
    - https://custom-domain.com/products/product-handle
    - https://store.myshopify.com/collections/*/products/product-handle

    Requirements: 1.3
    """

    PLATFORM_NAME = "shopify"
    URL_PATTERNS = [
        r"\.myshopify\.com/products/",
        r"/products/[a-zA-Z0-9\-_]+",
    ]

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
            InvalidURLError: If URL format is invalid
            ExtractionError: If extraction fails
        """
        log = self._log.bind(url=product_url)
        log.info("shopify_extraction_start")

        # Validate URL format
        self.validate_url(product_url)

        # Parse URL and construct JSON endpoint
        json_url = self._get_json_url(product_url)
        log.debug("shopify_json_url", json_url=json_url)

        try:
            # Fetch product JSON
            product_data = await self._fetch_product_json(json_url)

            # Parse product data
            product_info = self._parse_product_data(product_data)

            log.info(
                "shopify_extraction_success",
                title=product_info.title,
                price=product_info.price,
                image_count=len(product_info.images),
            )

            return product_info

        except aiohttp.ClientError as e:
            log.error("shopify_network_error", error=str(e))
            raise ExtractionError(
                message=f"Failed to fetch Shopify product: {str(e)}",
                error_code="6007",
                url=product_url,
                recoverable=True,
            )
        except KeyError as e:
            log.error("shopify_parse_error", error=str(e))
            raise ExtractionError(
                message=f"Failed to parse Shopify product data: missing {str(e)}",
                error_code="6007",
                url=product_url,
                recoverable=False,
            )

    def _get_json_url(self, product_url: str) -> str:
        """Convert product URL to JSON endpoint URL.

        Args:
            product_url: Original product URL

        Returns:
            URL to the product JSON endpoint

        Raises:
            InvalidURLError: If URL cannot be parsed
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
            raise InvalidURLError(
                product_url,
                "Could not extract product handle from URL",
            )

        # Reconstruct URL with JSON endpoint
        return f"{parsed.scheme}://{parsed.netloc}{json_path}"

    async def _fetch_product_json(self, json_url: str) -> dict:
        """Fetch product data from Shopify JSON endpoint.

        Args:
            json_url: URL to the product JSON endpoint

        Returns:
            Product data dictionary

        Raises:
            aiohttp.ClientError: On network errors
            ExtractionError: If response is not valid JSON or product not found
        """
        headers = {
            "User-Agent": self.USER_AGENT,
            "Accept": "application/json",
        }

        timeout = aiohttp.ClientTimeout(total=self.REQUEST_TIMEOUT)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(json_url, headers=headers) as response:
                if response.status == 404:
                    raise ExtractionError(
                        message="Product not found",
                        error_code="6007",
                        url=json_url,
                        recoverable=False,
                    )

                if response.status != 200:
                    raise ExtractionError(
                        message=f"Shopify returned status {response.status}",
                        error_code="6007",
                        url=json_url,
                        recoverable=response.status >= 500,
                    )

                try:
                    data = await response.json()
                except Exception as e:
                    raise ExtractionError(
                        message=f"Invalid JSON response: {str(e)}",
                        error_code="6007",
                        url=json_url,
                        recoverable=False,
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

        # Extract description (HTML)
        description_html = product.get("body_html", "")
        description = self._clean_html(description_html)

        # Extract selling points from description and tags
        selling_points = self._extract_selling_points(description)

        # Add tags as potential selling points
        tags = product.get("tags", [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",")]

        # Filter meaningful tags (not internal tags)
        meaningful_tags = [
            tag for tag in tags
            if len(tag) > 3 and not tag.startswith("_")
        ]
        selling_points.extend(meaningful_tags[:3])

        # Deduplicate selling points
        seen = set()
        unique_points = []
        for point in selling_points:
            if point.lower() not in seen:
                seen.add(point.lower())
                unique_points.append(point)

        return ProductInfo(
            title=title,
            price=price,
            currency=currency,
            images=images,
            description=description[:2000] if description else "",  # Limit length
            selling_points=unique_points[:5],
            source="shopify",
        )
