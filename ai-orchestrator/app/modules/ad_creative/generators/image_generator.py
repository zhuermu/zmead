"""
Image generator using Gemini Imagen 3.

Requirements: 4.2, 4.5, 4.1.4
- 4.2: Generate images using Gemini Imagen 3
- 4.5: Auto-retry up to 3 times on failure
- 4.1.4: Retry file upload up to 3 times
"""

import asyncio
import uuid
from datetime import datetime
from typing import Any

import structlog

from ..models import GeneratedImage, ProductInfo
from ..utils.aspect_ratio import AspectRatioHandler

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
    """Generates ad creative images using Gemini Imagen 3.

    Features:
    - Platform-aware aspect ratio selection
    - Parallel batch generation for efficiency
    - Exponential backoff retry on failures
    - Customizable styles and prompts
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
        gemini_client: Any = None,
        aspect_ratio_handler: AspectRatioHandler | None = None,
        max_retries: int = MAX_RETRIES,
    ):
        """Initialize image generator.

        Args:
            gemini_client: Gemini client for AI generation
            aspect_ratio_handler: Handler for aspect ratio operations
            max_retries: Maximum retry attempts (default 3)
        """
        self.gemini = gemini_client
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
    ) -> GeneratedImage:
        """Generate a single image with retry logic.

        Args:
            prompt: Generation prompt
            aspect_ratio: Aspect ratio string
            width: Image width
            height: Image height
            index: Image index for naming
            log: Bound logger

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
    ) -> GeneratedImage:
        """Generate a single image using Gemini Imagen 3.

        Args:
            prompt: Generation prompt
            aspect_ratio: Aspect ratio string
            width: Image width
            height: Image height
            index: Image index for naming

        Returns:
            Generated image
        """
        if self.gemini is None:
            raise ImageGenerationError(
                "Gemini client not configured",
                code="CONFIG_ERROR",
                retryable=False,
            )

        # Call Gemini Imagen 3 API
        # Note: The actual API call depends on the Gemini client implementation
        # This is a placeholder that should be replaced with actual API call
        try:
            image_data = await self._call_imagen_api(prompt, aspect_ratio)
        except Exception as e:
            raise ImageGenerationError(
                f"Imagen API call failed: {e}",
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

    async def _call_imagen_api(
        self,
        prompt: str,
        aspect_ratio: str,
    ) -> bytes:
        """Call Gemini Imagen 3 API to generate image.

        Args:
            prompt: Generation prompt
            aspect_ratio: Aspect ratio for the image

        Returns:
            Image bytes

        Note:
            This method should be implemented based on the actual
            Gemini Imagen 3 API. Currently uses a placeholder.
        """
        # Import here to avoid circular imports
        from app.core.config import get_settings

        settings = get_settings()

        # The actual implementation depends on the Gemini API
        # For now, we'll use the chat completion to describe what would be generated
        # In production, this should use the actual Imagen 3 API

        # Placeholder: In real implementation, use google.generativeai
        # import google.generativeai as genai
        # model = genai.ImageGenerationModel(settings.gemini_model_imagen)
        # response = await model.generate_images(
        #     prompt=prompt,
        #     number_of_images=1,
        #     aspect_ratio=aspect_ratio,
        #     safety_filter_level="block_some",
        # )
        # return response.images[0].image_bytes

        # For development/testing, return placeholder bytes
        # This should be replaced with actual API call in production
        raise NotImplementedError(
            "Imagen 3 API integration pending. "
            "Replace this with actual google.generativeai call."
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
    ) -> list[GeneratedImage]:
        """Generate variants based on an original image.

        Args:
            original_image_url: URL of the original image
            count: Number of variants to generate
            style: Optional style override

        Returns:
            List of generated variant images

        Note:
            This is a placeholder for variant generation.
            Implementation depends on Imagen 3 edit/variation capabilities.
        """
        raise NotImplementedError(
            "Variant generation not yet implemented. "
            "Requires Imagen 3 image-to-image capabilities."
        )
