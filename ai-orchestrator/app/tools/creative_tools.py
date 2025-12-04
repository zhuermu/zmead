"""Creative Tools for Ad Creative generation and analysis.

This module provides Agent Custom Tools for creative-related operations:
- generate_image_tool: Generate ad images using Gemini Imagen
- generate_video_tool: Generate ad videos using Gemini Veo
- analyze_creative_tool: Analyze creative quality using Gemini Vision
- extract_product_info_tool: Extract product information using Gemini

These tools can call LLMs (Gemini) for AI capabilities.
They call the module functions directly (not through capability.py).
"""

import base64
import structlog
from typing import Any

from app.services.gemini_client import GeminiClient, GeminiError
from app.services.gcs_client import GCSClient, GCSError, get_gcs_client
from app.services.mcp_client import MCPClient, MCPError
from app.tools.base import (
    AgentTool,
    ToolCategory,
    ToolExecutionError,
    ToolMetadata,
    ToolParameter,
)

logger = structlog.get_logger(__name__)


class GenerateImageTool(AgentTool):
    """Tool for generating ad images using Gemini Imagen.

    This tool calls Gemini Imagen to generate advertising images
    based on product information and style preferences.
    """

    def __init__(
        self,
        gemini_client: GeminiClient | None = None,
        mcp_client: MCPClient | None = None,
    ):
        """Initialize the generate image tool.

        Args:
            gemini_client: Gemini client for image generation
            mcp_client: MCP client for saving creatives
        """
        metadata = ToolMetadata(
            name="generate_image_tool",
            description=(
                "Generate advertising images using AI. "
                "Provide product information and style preferences to create "
                "professional ad creatives. Supports various aspect ratios for "
                "different platforms (TikTok, Instagram, Facebook)."
            ),
            category=ToolCategory.AGENT_CUSTOM,
            parameters=[
                ToolParameter(
                    name="product_info",
                    type="object",
                    description="Product information including name, description, features",
                    required=True,
                ),
                ToolParameter(
                    name="style",
                    type="string",
                    description="Visual style for the image",
                    required=True,
                    enum=["modern", "vibrant", "luxury", "minimal", "playful"],
                ),
                ToolParameter(
                    name="aspect_ratio",
                    type="string",
                    description="Image aspect ratio",
                    required=False,
                    default="1:1",
                    enum=["1:1", "16:9", "9:16", "4:3", "3:4"],
                ),
                ToolParameter(
                    name="count",
                    type="number",
                    description="Number of images to generate (1-4)",
                    required=False,
                    default=1,
                ),
            ],
            returns="object with image_urls and creative_ids",
            credit_cost=5.0,
            tags=["creative", "image", "generation", "ai"],
        )

        super().__init__(metadata)

        self.gemini_client = gemini_client or GeminiClient()
        self.mcp_client = mcp_client or MCPClient()

    async def execute(
        self,
        parameters: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute image generation.

        Args:
            parameters: Tool parameters
            context: Execution context with user_id

        Returns:
            Generated image URLs and creative IDs

        Raises:
            ToolExecutionError: If generation fails
        """
        user_id = context.get("user_id") if context else None
        product_info = parameters.get("product_info", {})
        style = parameters.get("style", "modern")
        aspect_ratio = parameters.get("aspect_ratio", "1:1")
        count = parameters.get("count", 1)

        log = logger.bind(
            tool=self.name,
            user_id=user_id,
            style=style,
            aspect_ratio=aspect_ratio,
            count=count,
        )
        log.info("generate_image_start")

        try:
            # Build prompt directly for simple image generation
            # This allows generating general images without full ProductInfo validation
            prompt = self._build_image_prompt(product_info, style)

            log.info("generating_image", prompt_preview=prompt[:100])

            # Generate images directly using Gemini client
            image_bytes_list = await self.gemini_client.generate_images(
                prompt=prompt,
                count=count,
                aspect_ratio=aspect_ratio,
                use_pro_model=False,
            )

            log.info("images_generated", count=len(image_bytes_list))

            # Save creatives via MCP (if MCP client is available and configured)
            creative_ids = []
            image_urls = []
            image_data_list = []

            for idx, image_bytes in enumerate(image_bytes_list):
                # Convert to base64 for transport/storage
                image_b64 = base64.b64encode(image_bytes).decode("utf-8")
                image_data_list.append({
                    "index": idx,
                    "format": "png",
                    "size": len(image_bytes),
                    "data_b64": image_b64,
                })

                # Try to save via MCP if available
                try:
                    result = await self.mcp_client.call_tool(
                        "save_creative",
                        {
                            "user_id": user_id,
                            "image_data": image_b64,
                            "metadata": {
                                "product_name": product_info.get("name", "generated_image"),
                                "style": style,
                                "aspect_ratio": aspect_ratio,
                                "generated_by": "gemini_imagen",
                                "prompt": prompt,
                            },
                        },
                    )

                    creative_ids.append(result.get("creative_id"))
                    image_urls.append(result.get("url"))

                except MCPError as e:
                    log.warning(
                        "save_creative_failed",
                        index=idx,
                        error=str(e),
                    )
                    # Still include the image data even if MCP save fails
                    creative_ids.append(None)
                    image_urls.append(None)

            log.info(
                "generate_image_complete",
                generated=len(image_bytes_list),
                saved=len([cid for cid in creative_ids if cid]),
            )

            return {
                "success": True,
                "image_urls": [url for url in image_urls if url],
                "creative_ids": [cid for cid in creative_ids if cid],
                "count": len(image_bytes_list),
                "images": image_data_list,  # Include raw image data for direct use
                "message": f"Successfully generated {len(image_bytes_list)} images",
            }

        except GeminiError as e:
            log.error("gemini_error", error=str(e))
            raise ToolExecutionError(
                message=f"Image generation failed: {e.message}",
                tool_name=self.name,
                error_code=e.code,
            )

        except MCPError as e:
            log.error("mcp_error", error=str(e))
            raise ToolExecutionError(
                message=f"Failed to save creatives: {e.message}",
                tool_name=self.name,
                error_code=e.code,
            )

        except Exception as e:
            log.error("unexpected_error", error=str(e), exc_info=True)
            raise ToolExecutionError(
                message=f"Unexpected error: {str(e)}",
                tool_name=self.name,
            )

    def _build_image_prompt(
        self,
        product_info: dict[str, Any],
        style: str,
    ) -> str:
        """Build image generation prompt.

        Args:
            product_info: Product information
            style: Visual style

        Returns:
            Generation prompt
        """
        product_name = product_info.get("name", "product")
        description = product_info.get("description", "")
        features = product_info.get("features", [])

        # Style-specific prompts
        style_prompts = {
            "modern": "clean, minimalist, contemporary design with bold typography",
            "vibrant": "colorful, energetic, eye-catching with bright colors",
            "luxury": "elegant, sophisticated, premium feel with gold accents",
            "minimal": "simple, clean, lots of white space, focused composition",
            "playful": "fun, dynamic, creative with playful elements",
        }

        style_desc = style_prompts.get(style, "professional advertising style")

        prompt = f"""Create a professional advertising image for {product_name}.

Product Description: {description}

Key Features:
{chr(10).join(f'- {feature}' for feature in features[:3])}

Style: {style_desc}

Requirements:
- High-quality, professional advertising photography
- Clear product focus
- Suitable for social media advertising
- Eye-catching and engaging
- No text or watermarks"""

        return prompt


class GenerateVideoTool(AgentTool):
    """Tool for generating ad videos using Gemini Veo.

    This tool calls Gemini Veo to generate advertising videos
    based on product information and creative direction.
    """

    def __init__(
        self,
        gemini_client: GeminiClient | None = None,
        mcp_client: MCPClient | None = None,
    ):
        """Initialize the generate video tool.

        Args:
            gemini_client: Gemini client for video generation
            mcp_client: MCP client for saving videos
        """
        metadata = ToolMetadata(
            name="generate_video_tool",
            description=(
                "Generate advertising videos using AI. "
                "Provide product information and creative direction to create "
                "engaging video ads. Supports various durations and aspect ratios."
            ),
            category=ToolCategory.AGENT_CUSTOM,
            parameters=[
                ToolParameter(
                    name="product_info",
                    type="object",
                    description="Product information including name, description, features",
                    required=True,
                ),
                ToolParameter(
                    name="style",
                    type="string",
                    description="Video style and mood",
                    required=True,
                    enum=["dynamic", "calm", "energetic", "professional", "lifestyle"],
                ),
                ToolParameter(
                    name="duration",
                    type="number",
                    description="Video duration in seconds",
                    required=False,
                    default=4,
                    enum=["4", "6", "8"],
                ),
                ToolParameter(
                    name="aspect_ratio",
                    type="string",
                    description="Video aspect ratio",
                    required=False,
                    default="16:9",
                    enum=["16:9", "9:16"],
                ),
            ],
            returns="object with operation_id for polling video status",
            credit_cost=20.0,
            tags=["creative", "video", "generation", "ai"],
        )

        super().__init__(metadata)

        self.gemini_client = gemini_client or GeminiClient()
        self.mcp_client = mcp_client or MCPClient()

    async def execute(
        self,
        parameters: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute video generation.

        Args:
            parameters: Tool parameters
            context: Execution context with user_id

        Returns:
            Video URL and metadata once generation completes

        Raises:
            ToolExecutionError: If generation fails
        """
        import asyncio

        user_id = context.get("user_id") if context else None
        product_info = parameters.get("product_info", {})
        style = parameters.get("style", "dynamic")
        duration = parameters.get("duration", 4)
        aspect_ratio = parameters.get("aspect_ratio", "16:9")

        log = logger.bind(
            tool=self.name,
            user_id=user_id,
            style=style,
            duration=duration,
            aspect_ratio=aspect_ratio,
        )
        log.info("generate_video_start")

        try:
            # Build generation prompt
            prompt = self._build_video_prompt(product_info, style)

            # Generate video using Gemini Veo
            result = await self.gemini_client.generate_video(
                prompt=prompt,
                duration=duration,
                aspect_ratio=aspect_ratio,
                use_fast_model=False,
            )

            operation_id = result.get("operation_id")

            log.info("video_generation_started", operation_id=operation_id)

            # Poll for completion (max 5 minutes with 5 second intervals)
            max_attempts = 60
            poll_interval = 5

            for attempt in range(max_attempts):
                poll_result = await self.gemini_client.poll_video_operation(operation_id)

                if poll_result.get("status") == "completed":
                    video_uri = poll_result.get("video_uri")
                    video_bytes = poll_result.get("video_bytes")

                    log.info(
                        "video_generation_complete",
                        operation_id=operation_id,
                        video_uri=video_uri[:100] if video_uri else None,
                        has_video_bytes=video_bytes is not None,
                    )

                    result = {
                        "success": True,
                        "status": "completed",
                        "operation_id": operation_id,
                        "message": "Video generated successfully",
                    }

                    # Upload video to GCS for persistent public access
                    if video_bytes:
                        try:
                            gcs_client = get_gcs_client()
                            product_name = product_info.get("name", "video")
                            filename = f"{product_name}_{style}_{operation_id[-8:]}.mp4"

                            upload_result = await gcs_client.upload_video(
                                video_bytes=video_bytes,
                                filename=filename,
                                user_id=user_id or "anonymous",
                                content_type="video/mp4",
                                prefix="chat-videos",
                                metadata={
                                    "style": style,
                                    "duration": str(duration),
                                    "aspect_ratio": aspect_ratio,
                                    "operation_id": operation_id,
                                },
                            )

                            # Return object_name for signed URL generation
                            result["video_object_name"] = upload_result["object_name"]
                            result["video_bucket"] = upload_result["bucket"]
                            result["video_gcs_url"] = upload_result["gcs_url"]
                            log.info(
                                "video_uploaded_to_gcs",
                                object_name=upload_result["object_name"],
                                size=upload_result["size"],
                            )
                        except GCSError as e:
                            log.warning(
                                "gcs_upload_failed",
                                error=str(e),
                            )
                            # Fallback to base64 if GCS upload fails
                            video_data_b64 = poll_result.get("video_data_b64")
                            if video_data_b64:
                                result["video_data_b64"] = video_data_b64
                                result["video_format"] = "mp4"
                    elif video_uri:
                        # Fallback to URI (may require auth)
                        result["video_url"] = video_uri

                    return result

                # Still processing
                progress = poll_result.get("progress", 0)
                log.info(
                    "video_generation_polling",
                    attempt=attempt + 1,
                    progress=progress,
                )

                await asyncio.sleep(poll_interval)

            # Timeout
            log.warning("video_generation_timeout", operation_id=operation_id)
            return {
                "success": False,
                "status": "timeout",
                "operation_id": operation_id,
                "message": "Video generation timed out. Please check back later.",
            }

        except GeminiError as e:
            log.error("gemini_error", error=str(e))
            raise ToolExecutionError(
                message=f"Video generation failed: {e.message}",
                tool_name=self.name,
                error_code=e.code,
            )

        except Exception as e:
            log.error("unexpected_error", error=str(e), exc_info=True)
            raise ToolExecutionError(
                message=f"Unexpected error: {str(e)}",
                tool_name=self.name,
            )

    def _build_video_prompt(
        self,
        product_info: dict[str, Any],
        style: str,
    ) -> str:
        """Build video generation prompt.

        Args:
            product_info: Product information
            style: Video style

        Returns:
            Generation prompt
        """
        product_name = product_info.get("name", "product")
        description = product_info.get("description", "")

        # Style-specific prompts
        style_prompts = {
            "dynamic": "fast-paced, energetic movements, quick cuts",
            "calm": "smooth, flowing movements, peaceful atmosphere",
            "energetic": "vibrant, exciting, high-energy visuals",
            "professional": "clean, corporate, professional presentation",
            "lifestyle": "natural, relatable, everyday use scenarios",
        }

        style_desc = style_prompts.get(style, "professional advertising style")

        prompt = f"""Create a professional advertising video for {product_name}.

Product: {description}

Style: {style_desc}

Requirements:
- High-quality, professional video production
- Clear product showcase
- Engaging and attention-grabbing
- Suitable for social media advertising
- No text overlays"""

        return prompt


class AnalyzeCreativeTool(AgentTool):
    """Tool for analyzing creative quality using Gemini Vision.

    This tool uses Gemini Vision to analyze ad creatives and provide
    insights on composition, color, messaging, and effectiveness.
    """

    def __init__(self, gemini_client: GeminiClient | None = None):
        """Initialize the analyze creative tool.

        Args:
            gemini_client: Gemini client for vision analysis
        """
        metadata = ToolMetadata(
            name="analyze_creative_tool",
            description=(
                "Analyze advertising creative quality using AI vision. "
                "Provides insights on composition, color scheme, messaging, "
                "and recommendations for improvement."
            ),
            category=ToolCategory.AGENT_CUSTOM,
            parameters=[
                ToolParameter(
                    name="image_url",
                    type="string",
                    description="URL of the image to analyze",
                    required=True,
                ),
            ],
            returns="object with analysis insights and recommendations",
            credit_cost=2.0,
            tags=["creative", "analysis", "vision", "ai"],
        )

        super().__init__(metadata)

        self.gemini_client = gemini_client or GeminiClient()

    async def execute(
        self,
        parameters: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute creative analysis.

        Args:
            parameters: Tool parameters
            context: Execution context

        Returns:
            Analysis insights and recommendations

        Raises:
            ToolExecutionError: If analysis fails
        """
        image_url = parameters.get("image_url")

        log = logger.bind(tool=self.name, image_url=image_url)
        log.info("analyze_creative_start")

        try:
            # Build analysis prompt
            prompt = """Analyze this advertising creative and provide detailed insights:

1. Composition: Layout, focal points, visual hierarchy
2. Color Scheme: Color palette, contrast, mood
3. Messaging: Visual storytelling, clarity, appeal
4. Effectiveness: Attention-grabbing, memorability, call-to-action

Provide specific, actionable recommendations for improvement."""

            # Analyze using Gemini Vision
            # Note: This is a simplified version. Full implementation would
            # download the image and pass it to Gemini Vision API
            messages = [
                {
                    "role": "user",
                    "content": f"{prompt}\n\nImage URL: {image_url}",
                }
            ]

            analysis_text = await self.gemini_client.chat_completion(
                messages=messages,
                temperature=0.3,
            )

            log.info("analyze_creative_complete")

            return {
                "success": True,
                "analysis": analysis_text,
                "image_url": image_url,
                "message": "Creative analysis completed",
            }

        except GeminiError as e:
            log.error("gemini_error", error=str(e))
            raise ToolExecutionError(
                message=f"Creative analysis failed: {e.message}",
                tool_name=self.name,
                error_code=e.code,
            )

        except Exception as e:
            log.error("unexpected_error", error=str(e), exc_info=True)
            raise ToolExecutionError(
                message=f"Unexpected error: {str(e)}",
                tool_name=self.name,
            )


class ExtractProductInfoTool(AgentTool):
    """Tool for extracting product information using Gemini.

    This tool uses Gemini to extract structured product information
    from product URLs or descriptions.
    """

    def __init__(self, gemini_client: GeminiClient | None = None):
        """Initialize the extract product info tool.

        Args:
            gemini_client: Gemini client for information extraction
        """
        metadata = ToolMetadata(
            name="extract_product_info_tool",
            description=(
                "Extract structured product information from URLs or descriptions. "
                "Returns product name, description, features, and other relevant details."
            ),
            category=ToolCategory.AGENT_CUSTOM,
            parameters=[
                ToolParameter(
                    name="url",
                    type="string",
                    description="Product URL (Shopify, Amazon, etc.)",
                    required=False,
                ),
                ToolParameter(
                    name="description",
                    type="string",
                    description="Product description text",
                    required=False,
                ),
            ],
            returns="object with structured product information",
            credit_cost=1.0,
            tags=["product", "extraction", "ai"],
        )

        super().__init__(metadata)

        self.gemini_client = gemini_client or GeminiClient()

    async def execute(
        self,
        parameters: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute product information extraction.

        Args:
            parameters: Tool parameters
            context: Execution context

        Returns:
            Structured product information

        Raises:
            ToolExecutionError: If extraction fails
        """
        url = parameters.get("url")
        description = parameters.get("description")

        log = logger.bind(tool=self.name, has_url=bool(url), has_description=bool(description))
        log.info("extract_product_info_start")

        if not url and not description:
            raise ToolExecutionError(
                message="Either url or description must be provided",
                tool_name=self.name,
                error_code="INVALID_PARAMS",
            )

        try:
            # Build extraction prompt
            if url:
                prompt = f"""Extract structured product information from this URL: {url}

Provide the following information:
- Product name
- Description (2-3 sentences)
- Key features (3-5 bullet points)
- Target audience
- Price range (if available)

Format as JSON."""
            else:
                prompt = f"""Extract structured product information from this description:

{description}

Provide the following information:
- Product name
- Description (2-3 sentences)
- Key features (3-5 bullet points)
- Target audience

Format as JSON."""

            # Extract using Gemini
            messages = [{"role": "user", "content": prompt}]

            result_text = await self.gemini_client.chat_completion(
                messages=messages,
                temperature=0.1,
            )

            log.info("extract_product_info_complete")

            # Parse JSON response
            import json

            try:
                product_info = json.loads(result_text)
            except json.JSONDecodeError:
                # If not valid JSON, return as text
                product_info = {"raw_text": result_text}

            return {
                "success": True,
                "product_info": product_info,
                "message": "Product information extracted successfully",
            }

        except GeminiError as e:
            log.error("gemini_error", error=str(e))
            raise ToolExecutionError(
                message=f"Product extraction failed: {e.message}",
                tool_name=self.name,
                error_code=e.code,
            )

        except Exception as e:
            log.error("unexpected_error", error=str(e), exc_info=True)
            raise ToolExecutionError(
                message=f"Unexpected error: {str(e)}",
                tool_name=self.name,
            )


# Factory function to create all creative tools
def create_creative_tools(
    gemini_client: GeminiClient | None = None,
    mcp_client: MCPClient | None = None,
) -> list[AgentTool]:
    """Create all creative tools.

    Args:
        gemini_client: Gemini client instance
        mcp_client: MCP client instance

    Returns:
        List of creative tools
    """
    return [
        GenerateImageTool(gemini_client=gemini_client, mcp_client=mcp_client),
        GenerateVideoTool(gemini_client=gemini_client, mcp_client=mcp_client),
        AnalyzeCreativeTool(gemini_client=gemini_client),
        ExtractProductInfoTool(gemini_client=gemini_client),
    ]
