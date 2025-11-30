"""
Image generator using Gemini native image generation.

Requirements: 4.2, 4.5, 4.1.4
- 4.2: Generate images using Gemini (gemini-2.0-flash-exp or gemini-2.5-pro-preview-image)
- 4.5: Auto-retry up to 3 times on failure
- 4.1.4: Retry file upload up to 3 times
"""

import asyncio
import uuid
from datetime import datetime
from typing import Any

import httpx
import structlog

from ..models import GeneratedImage, ProductInfo
from ..utils.aspect_ratio import AspectRatioHandler
from app.services.gemini_client import GeminiClient, GeminiImageGenerationError

logger = structlog.get_logger(__name__)


class ImageGenerationError(Exception):
    """Error during image generation."""

    def __init__(
        self,
        message: str,
        code: str = "GENERATION_FAILED",
        retryable: bool = True,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.retryable = retryable


class ImageGenerator:
    """Generates ad creative images using Gemini native image generation.

    Features:
    - Platform-aware aspect ratio selection
    - Parallel batch generation for efficiency
    - Exponential backoff retry on failures
    - Customizable styles and prompts
    - Image-to-image generation with reference images
    - Text-to-image generation
    """

    # Supported styles for image generation
    SUPPORTED_STYLES = {
        "modern": "modern, clean, minimalist design with bold typography",
        "minimal": "minimalist, simple, elegant with lots of white space",
        "vibrant": "vibrant, colorful, energetic with dynamic composition",
        "professional": "professional, corporate, trustworthy appearance",
        "playful": "playful, fun, casual with bright colors",
        "luxury": "luxury, premium, sophisticated with elegant details",
        "tech": "tech-forward, futuristic, innovative design",
        "natural": "natural, organic, eco-friendly aesthetic",
    }

    # Default generation parameters
    DEFAULT_STYLE = "modern"
    MAX_CONCURRENT_GENERATIONS = 5  # Limit concurrent API calls
    MAX_RETRIES = 3
    RETRY_BASE_DELAY = 1.0  # seconds
    RETRY_BACKOFF_FACTOR = 2.0

    def __init__(
        self,
        gemini_client: GeminiClient | None = None,
        aspect_ratio_handler: AspectRatioHandler | None = None,
        max_retries: int = MAX_RETRIES,
    ):
        """Initialize image generator.

        Args:
            gemini_client: Gemini client for AI generation (with image generation support)
            aspect_ratio_handler: Handler for aspect ratio operations
            max_retries: Maximum retry attempts (default 3)
        """
        self.gemini = gemini_client or GeminiClient()
        self.aspect_handler = aspect_ratio_handler or AspectRatioHandler()
        self.max_retries = max_retries
        self._semaphore = asyncio.Semaphore(self.MAX_CONCURRENT_GENERATIONS)

    async def generate(
        self,
        product_info: ProductInfo,
        count: int,
        style: str,
        aspect_ratio: str,
    ) -> list[GeneratedImage]:
        """Generate creative images.

        Args:
            product_info: Product information for prompt generation
            count: Number of images to generate (3 or 10)
            style: Style (modern, minimal, vibrant, etc.)
            aspect_ratio: Aspect ratio (9:16, 1:1, 4:5)

        Returns:
            List of generated images

        Raises:
            ImageGenerationError: If generation fails after retries
        """
        log = logger.bind(
            product_title=product_info.title,
            count=count,
            style=style,
            aspect_ratio=aspect_ratio,
        )
        log.info("image_generation_start")

        # Validate and get dimensions
        try:
            width, height = self.aspect_handler.get_dimensions(aspect_ratio)
        except ValueError as e:
            raise ImageGenerationError(
                f"Invalid aspect ratio: {e}",
                code="INVALID_ASPECT_RATIO",
                retryable=False,
            )

        # Build prompt
        prompt = self._build_prompt(product_info, style)

        # Generate images in parallel with concurrency limit
        tasks = [
            self._generate_single_with_retry(
                prompt=prompt,
                aspect_ratio=aspect_ratio,
                width=width,
                height=height,
                index=i,
                log=log,
            )
            for i in range(count)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        images: list[GeneratedImage] = []
        errors: list[Exception] = []

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                errors.append(result)
                log.warning("image_generation_partial_failure", index=i, error=str(result))
            else:
                images.append(result)

        # If all failed, raise error
        if not images:
            error_msg = f"All {count} image generations failed"
            log.error("image_generation_all_failed", errors=[str(e) for e in errors])
            raise ImageGenerationError(error_msg, code="4003", retryable=True)

        log.info(
            "image_generation_complete",
            generated=len(images),
            failed=len(errors),
        )

        return images

    async def _generate_single_with_retry(
        self,
        prompt: str,
        aspect_ratio: str,
        width: int,
        height: int,
        index: int,
        log: Any,
        reference_images: list[bytes] | None = None,
        use_pro_model: bool = False,
    ) -> GeneratedImage:
        """Generate a single image with retry logic.

        Args:
            prompt: Generation prompt
            aspect_ratio: Aspect ratio string
            width: Image width
            height: Image height
            index: Image index for naming
            log: Bound logger
            reference_images: Optional reference images for image-to-image
            use_pro_model: Use pro model for higher quality

        Returns:
            Generated image

        Raises:
            ImageGenerationError: If all retries fail
        """
        last_error: Exception | None = None

        for attempt in range(self.max_retries):
            try:
                async with self._semaphore:
                    return await self._generate_single(
                        prompt=prompt,
                        aspect_ratio=aspect_ratio,
                        width=width,
                        height=height,
                        index=index,
                        reference_images=reference_images,
                        use_pro_model=use_pro_model,
                    )
            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    wait_time = self.RETRY_BASE_DELAY * (
                        self.RETRY_BACKOFF_FACTOR ** attempt
                    )
                    log.warning(
                        "image_generation_retry",
                        index=index,
                        attempt=attempt + 1,
                        max_retries=self.max_retries,
                        wait_seconds=wait_time,
                        error=str(e),
                    )
                    await asyncio.sleep(wait_time)

        raise ImageGenerationError(
            f"Image generation failed after {self.max_retries} attempts: {last_error}",
            code="4003",
            retryable=False,
        )

    async def _generate_single(
        self,
        prompt: str,
        aspect_ratio: str,
        width: int,
        height: int,
        index: int,
        reference_images: list[bytes] | None = None,
        use_pro_model: bool = False,
    ) -> GeneratedImage:
        """Generate a single image using Gemini native image generation.

        Args:
            prompt: Generation prompt
            aspect_ratio: Aspect ratio string
            width: Image width
            height: Image height
            index: Image index for naming
            reference_images: Optional reference images for image-to-image
            use_pro_model: Use pro model for higher quality

        Returns:
            Generated image
        """
        if self.gemini is None:
            raise ImageGenerationError(
                "Gemini client not configured",
                code="CONFIG_ERROR",
                retryable=False,
            )

        # Call Gemini image generation API
        try:
            image_data = await self.gemini.generate_image(
                prompt=prompt,
                aspect_ratio=aspect_ratio,
                use_pro_model=use_pro_model,
                reference_images=reference_images,
            )
        except GeminiImageGenerationError as e:
            raise ImageGenerationError(
                f"Gemini image generation failed: {e}",
                code="AI_MODEL_FAILED",
                retryable=e.retryable,
            )
        except Exception as e:
            raise ImageGenerationError(
                f"Image generation API call failed: {e}",
                code="AI_MODEL_FAILED",
                retryable=True,
            )

        # Generate unique filename
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        unique_id = uuid.uuid4().hex[:8]
        file_name = f"creative_{timestamp}_{index + 1}_{unique_id}.png"

        return GeneratedImage(
            image_data=image_data,
            file_name=file_name,
            file_type="image/png",
            width=width,
            height=height,
            aspect_ratio=aspect_ratio,
        )

    def _build_prompt(self, product_info: ProductInfo, style: str) -> str:
        """Build generation prompt from product info and style.

        Args:
            product_info: Product information
            style: Style name or description

        Returns:
            Formatted prompt string
        """
        # Get style description
        style_desc = self.SUPPORTED_STYLES.get(
            style.lower(),
            style,  # Use as-is if not in predefined styles
        )

        # Extract key selling points (max 3)
        selling_points = product_info.selling_points[:3]
        selling_points_text = ", ".join(selling_points) if selling_points else "high quality"

        # Build prompt
        prompt = f"""Create a professional advertising image for an e-commerce product.

Product: {product_info.title}
Price: {product_info.currency} {product_info.price:.2f}
Key Features: {selling_points_text}

Style Requirements:
- {style_desc}
- High quality, professional advertising image
- Clear product focus with appealing presentation
- Suitable for social media advertising
- Eye-catching and engaging for target audience
- Clean background that highlights the product

Do NOT include:
- Watermarks or logos
- Text overlays (unless specifically requested)
- Distracting elements
- Low quality or blurry elements
"""
        return prompt.strip()

    async def generate_variants(
        self,
        original_image_url: str,
        count: int,
        style: str | None = None,
        aspect_ratio: str = "1:1",
    ) -> list[GeneratedImage]:
        """Generate variants based on an original image (image-to-image).

        Args:
            original_image_url: URL of the original image
            count: Number of variants to generate
            style: Optional style override
            aspect_ratio: Aspect ratio for generated images

        Returns:
            List of generated variant images

        Raises:
            ImageGenerationError: If variant generation fails
        """
        log = logger.bind(
            original_url=original_image_url[:50],
            count=count,
            style=style,
        )
        log.info("generate_variants_start")

        # Download the original image
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(original_image_url)
                response.raise_for_status()
                original_image_bytes = response.content
        except Exception as e:
            raise ImageGenerationError(
                f"Failed to download original image: {e}",
                code="IMAGE_DOWNLOAD_FAILED",
                retryable=True,
            )

        # Build variation prompt
        style_desc = self.SUPPORTED_STYLES.get(
            style.lower() if style else self.DEFAULT_STYLE,
            style or self.DEFAULT_STYLE,
        )

        prompt = f"""Create a variation of this image for advertising purposes.
Keep the main subject and composition but apply the following style:
- Style: {style_desc}
- Make it suitable for social media advertising
- Maintain high quality and professional look
- Add subtle variations while keeping the core visual identity"""

        # Get dimensions for aspect ratio
        try:
            width, height = self.aspect_handler.get_dimensions(aspect_ratio)
        except ValueError:
            width, height = 1024, 1024  # Default to 1:1

        # Generate variants with reference image
        tasks = [
            self._generate_single_with_retry(
                prompt=prompt,
                aspect_ratio=aspect_ratio,
                width=width,
                height=height,
                index=i,
                log=log,
                reference_images=[original_image_bytes],
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

        if not variants:
            error_msg = f"All {count} variant generations failed"
            log.error("variant_generation_all_failed", errors=[str(e) for e in errors])
            raise ImageGenerationError(error_msg, code="4003", retryable=True)

        log.info(
            "generate_variants_complete",
            generated=len(variants),
            failed=len(errors),
        )

        return variants

    async def generate_from_reference(
        self,
        reference_urls: list[str],
        prompt: str,
        count: int = 3,
        style: str = "modern",
        aspect_ratio: str = "1:1",
        use_pro_model: bool = False,
    ) -> list[GeneratedImage]:
        """Generate new images based on reference images (image-to-image).

        Args:
            reference_urls: URLs of reference images (1-14 images supported)
            prompt: Description of desired output
            count: Number of images to generate
            style: Style to apply
            aspect_ratio: Aspect ratio for output
            use_pro_model: Use pro model for higher quality

        Returns:
            List of generated images

        Raises:
            ImageGenerationError: If generation fails
        """
        log = logger.bind(
            reference_count=len(reference_urls),
            prompt=prompt[:50],
            count=count,
            style=style,
        )
        log.info("generate_from_reference_start")

        # Download reference images
        reference_images: list[bytes] = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            for url in reference_urls[:14]:  # Max 14 reference images
                try:
                    response = await client.get(url)
                    response.raise_for_status()
                    reference_images.append(response.content)
                except Exception as e:
                    log.warning("reference_download_failed", url=url[:50], error=str(e))

        if not reference_images:
            raise ImageGenerationError(
                "Failed to download any reference images",
                code="IMAGE_DOWNLOAD_FAILED",
                retryable=True,
            )

        # Build enhanced prompt
        style_desc = self.SUPPORTED_STYLES.get(style.lower(), style)
        enhanced_prompt = f"""Based on the reference image(s), create a new advertising creative.

{prompt}

Style requirements:
- {style_desc}
- Professional advertising quality
- Clear product focus
- Suitable for social media platforms

Maintain visual consistency with the references while creating something unique."""

        # Get dimensions
        try:
            width, height = self.aspect_handler.get_dimensions(aspect_ratio)
        except ValueError:
            width, height = 1024, 1024

        # Generate images
        tasks = [
            self._generate_single_with_retry(
                prompt=enhanced_prompt,
                aspect_ratio=aspect_ratio,
                width=width,
                height=height,
                index=i,
                log=log,
                reference_images=reference_images,
                use_pro_model=use_pro_model,
            )
            for i in range(count)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        images: list[GeneratedImage] = []
        errors: list[Exception] = []

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                errors.append(result)
                log.warning("reference_generation_partial_failure", index=i, error=str(result))
            else:
                images.append(result)

        if not images:
            error_msg = f"All {count} reference-based generations failed"
            log.error("reference_generation_all_failed", errors=[str(e) for e in errors[:3]])
            raise ImageGenerationError(error_msg, code="4003", retryable=True)

        log.info(
            "generate_from_reference_complete",
            generated=len(images),
            failed=len(errors),
        )

        return images

    async def close(self):
        """Close resources (Gemini client HTTP connections)."""
        if self.gemini:
            await self.gemini.close()
