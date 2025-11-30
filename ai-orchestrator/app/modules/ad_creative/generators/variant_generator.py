"""
Variant generator for creating variations of existing creatives.

Requirements: 6.4
- Generate variants based on original creative
- Support different variation types (color, composition, style)
- Maintain aspect ratio from original
"""

import asyncio
import uuid
from datetime import datetime
from typing import Any, Literal

import structlog

from app.services.mcp_client import MCPClient, MCPError

from ..models import GeneratedImage, Creative
from ..utils.aspect_ratio import AspectRatioHandler

logger = structlog.get_logger(__name__)


class VariantGenerationError(Exception):
    """Error during variant generation."""

    def __init__(
        self,
        message: str,
        code: str = "VARIANT_GENERATION_FAILED",
        retryable: bool = True,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.retryable = retryable


class VariantGenerator:
    """Generates variants based on existing creatives.

    Features:
    - Multiple variation types (color, composition, style)
    - Maintains original aspect ratio
    - Parallel generation with concurrency control
    - Exponential backoff retry on failures

    Example:
        generator = VariantGenerator(gemini_client, mcp_client)
        variants = await generator.generate_variants(
            user_id="user123",
            creative_id="creative456",
            count=3,
            variation_type="style"
        )
    """

    # Variation types and their prompts
    VARIATION_TYPES = {
        "color": "Create a color variation with different color palette while maintaining the same composition and subject",
        "composition": "Create a composition variation with different layout and arrangement while keeping the same subject and colors",
        "style": "Create a style variation with different artistic style while maintaining the same subject and message",
        "lighting": "Create a lighting variation with different lighting conditions while keeping the same composition",
        "background": "Create a background variation with different background while keeping the same subject",
    }

    MAX_CONCURRENT_GENERATIONS = 3
    MAX_RETRIES = 3
    RETRY_BASE_DELAY = 1.0
    RETRY_BACKOFF_FACTOR = 2.0

    def __init__(
        self,
        gemini_client: Any = None,
        mcp_client: MCPClient | None = None,
        aspect_ratio_handler: AspectRatioHandler | None = None,
    ):
        """Initialize variant generator.

        Args:
            gemini_client: Gemini client for AI generation
            mcp_client: MCP client for fetching original creative
            aspect_ratio_handler: Handler for aspect ratio operations
        """
        self.gemini = gemini_client
        self.mcp = mcp_client
        self.aspect_handler = aspect_ratio_handler or AspectRatioHandler()
        self._semaphore = asyncio.Semaphore(self.MAX_CONCURRENT_GENERATIONS)

    async def generate_variants(
        self,
        user_id: str,
        creative_id: str,
        count: int,
        variation_type: Literal["color", "composition", "style", "lighting", "background"] = "style",
    ) -> list[GeneratedImage]:
        """Generate variants of an existing creative.

        Args:
            user_id: User ID for authorization
            creative_id: ID of the original creative
            count: Number of variants to generate (1-5)
            variation_type: Type of variation to create

        Returns:
            List of generated variant images

        Raises:
            VariantGenerationError: If generation fails
        """
        log = logger.bind(
            user_id=user_id,
            creative_id=creative_id,
            count=count,
            variation_type=variation_type,
        )
        log.info("variant_generation_start")

        # Validate count
        if count < 1 or count > 5:
            raise VariantGenerationError(
                "Variant count must be between 1 and 5",
                code="INVALID_COUNT",
                retryable=False,
            )

        # Validate variation type
        if variation_type not in self.VARIATION_TYPES:
            raise VariantGenerationError(
                f"Invalid variation type: {variation_type}. "
                f"Supported types: {list(self.VARIATION_TYPES.keys())}",
                code="INVALID_VARIATION_TYPE",
                retryable=False,
            )

        # Fetch original creative
        original = await self._fetch_original_creative(user_id, creative_id)
        log.info("original_creative_fetched", url=original.url)

        # Get dimensions from original aspect ratio
        try:
            width, height = self.aspect_handler.get_dimensions(original.aspect_ratio)
        except ValueError:
            # Default to 1:1 if aspect ratio is invalid
            width, height = 1080, 1080

        # Build variation prompt
        prompt = self._build_variation_prompt(original, variation_type)

        # Generate variants in parallel
        tasks = [
            self._generate_single_variant_with_retry(
                original_url=original.url,
                prompt=prompt,
                aspect_ratio=original.aspect_ratio,
                width=width,
                height=height,
                index=i,
                log=log,
            )
            for i in range(count)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        variants: list[GeneratedImage] = []
        errors: list[Exception] = []

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                errors.append(result)
                log.warning("variant_generation_partial_failure", index=i, error=str(result))
            else:
                variants.append(result)

        # If all failed, raise error
        if not variants:
            error_msg = f"All {count} variant generations failed"
            log.error("variant_generation_all_failed", errors=[str(e) for e in errors])
            raise VariantGenerationError(error_msg, code="4003", retryable=True)

        log.info(
            "variant_generation_complete",
            generated=len(variants),
            failed=len(errors),
        )

        return variants

    async def _fetch_original_creative(
        self,
        user_id: str,
        creative_id: str,
    ) -> Creative:
        """Fetch the original creative from Web Platform.

        Args:
            user_id: User ID
            creative_id: Creative ID

        Returns:
            Original creative data

        Raises:
            VariantGenerationError: If creative not found
        """
        if self.mcp is None:
            raise VariantGenerationError(
                "MCP client not initialized",
                code="MCP_NOT_INITIALIZED",
                retryable=False,
            )

        try:
            result = await self.mcp.call_tool(
                "get_creative",
                {
                    "user_id": user_id,
                    "creative_id": creative_id,
                },
            )

            return Creative(
                creative_id=result.get("creative_id", creative_id),
                user_id=result.get("user_id", user_id),
                url=result.get("url", result.get("file_url", "")),
                thumbnail_url=result.get("thumbnail_url"),
                product_url=result.get("product_url"),
                style=result.get("style"),
                aspect_ratio=result.get("aspect_ratio", "1:1"),
                platform=result.get("platform"),
                score=result.get("score"),
                score_dimensions=result.get("score_dimensions"),
                created_at=result.get("created_at", ""),
                updated_at=result.get("updated_at"),
                tags=result.get("tags", []),
            )

        except MCPError as e:
            if e.code == "RESOURCE_NOT_FOUND":
                raise VariantGenerationError(
                    f"Original creative not found: {creative_id}",
                    code="CREATIVE_NOT_FOUND",
                    retryable=False,
                ) from e
            raise VariantGenerationError(
                f"Failed to fetch original creative: {e.message}",
                code=e.code or "MCP_ERROR",
                retryable=True,
            ) from e

    def _build_variation_prompt(
        self,
        original: Creative,
        variation_type: str,
    ) -> str:
        """Build prompt for variant generation.

        Args:
            original: Original creative
            variation_type: Type of variation

        Returns:
            Formatted prompt string
        """
        variation_instruction = self.VARIATION_TYPES[variation_type]

        prompt = f"""Based on the provided reference image, create a variant.

Variation Type: {variation_type}
Instructions: {variation_instruction}

Requirements:
- Maintain the same product/subject as the original
- Keep the same aspect ratio ({original.aspect_ratio})
- Create a distinct but related variation
- Maintain professional advertising quality
- Suitable for social media advertising

Original Style: {original.style or 'modern'}
Original Platform: {original.platform or 'general'}

Do NOT:
- Change the core product/subject
- Add watermarks or logos
- Create something completely unrelated
"""
        return prompt.strip()

    async def _generate_single_variant_with_retry(
        self,
        original_url: str,
        prompt: str,
        aspect_ratio: str,
        width: int,
        height: int,
        index: int,
        log: Any,
    ) -> GeneratedImage:
        """Generate a single variant with retry logic.

        Args:
            original_url: URL of the original image
            prompt: Generation prompt
            aspect_ratio: Aspect ratio string
            width: Image width
            height: Image height
            index: Variant index
            log: Bound logger

        Returns:
            Generated variant image

        Raises:
            VariantGenerationError: If all retries fail
        """
        last_error: Exception | None = None

        for attempt in range(self.MAX_RETRIES):
            try:
                async with self._semaphore:
                    return await self._generate_single_variant(
                        original_url=original_url,
                        prompt=prompt,
                        aspect_ratio=aspect_ratio,
                        width=width,
                        height=height,
                        index=index,
                    )
            except Exception as e:
                last_error = e
                if attempt < self.MAX_RETRIES - 1:
                    wait_time = self.RETRY_BASE_DELAY * (
                        self.RETRY_BACKOFF_FACTOR ** attempt
                    )
                    log.warning(
                        "variant_generation_retry",
                        index=index,
                        attempt=attempt + 1,
                        max_retries=self.MAX_RETRIES,
                        wait_seconds=wait_time,
                        error=str(e),
                    )
                    await asyncio.sleep(wait_time)

        raise VariantGenerationError(
            f"Variant generation failed after {self.MAX_RETRIES} attempts: {last_error}",
            code="4003",
            retryable=False,
        )

    async def _generate_single_variant(
        self,
        original_url: str,
        prompt: str,
        aspect_ratio: str,
        width: int,
        height: int,
        index: int,
    ) -> GeneratedImage:
        """Generate a single variant using Gemini.

        Args:
            original_url: URL of the original image
            prompt: Generation prompt
            aspect_ratio: Aspect ratio string
            width: Image width
            height: Image height
            index: Variant index

        Returns:
            Generated variant image
        """
        if self.gemini is None:
            raise VariantGenerationError(
                "Gemini client not configured",
                code="CONFIG_ERROR",
                retryable=False,
            )

        # Call Gemini API for image-to-image generation
        try:
            image_data = await self._call_gemini_variant_api(
                original_url=original_url,
                prompt=prompt,
                aspect_ratio=aspect_ratio,
            )
        except Exception as e:
            raise VariantGenerationError(
                f"Gemini API call failed: {e}",
                code="AI_MODEL_FAILED",
                retryable=True,
            )

        # Generate unique filename
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        unique_id = uuid.uuid4().hex[:8]
        file_name = f"variant_{timestamp}_{index + 1}_{unique_id}.png"

        return GeneratedImage(
            image_data=image_data,
            file_name=file_name,
            file_type="image/png",
            width=width,
            height=height,
            aspect_ratio=aspect_ratio,
        )

    async def _call_gemini_variant_api(
        self,
        original_url: str,
        prompt: str,
        aspect_ratio: str,
    ) -> bytes:
        """Call Gemini API for variant generation.

        Args:
            original_url: URL of the original image
            prompt: Generation prompt
            aspect_ratio: Aspect ratio for the variant

        Returns:
            Image bytes

        Note:
            This method should be implemented based on the actual
            Gemini Imagen 3 image-to-image API. Currently uses a placeholder.
        """
        # The actual implementation depends on the Gemini API
        # For image-to-image generation, we would use:
        #
        # import google.generativeai as genai
        # model = genai.ImageGenerationModel("imagen-3.0-generate-001")
        #
        # # Download original image
        # original_image = await self._download_image(original_url)
        #
        # # Generate variant using image-to-image
        # response = await model.generate_images(
        #     prompt=prompt,
        #     reference_images=[original_image],
        #     number_of_images=1,
        #     aspect_ratio=aspect_ratio,
        #     safety_filter_level="block_some",
        # )
        # return response.images[0].image_bytes

        # For development/testing, raise NotImplementedError
        # This should be replaced with actual API call in production
        raise NotImplementedError(
            "Gemini image-to-image API integration pending. "
            "Replace this with actual google.generativeai call."
        )

    async def _download_image(self, url: str) -> bytes:
        """Download image from URL.

        Args:
            url: Image URL

        Returns:
            Image bytes
        """
        import httpx

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.content
