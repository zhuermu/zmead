"""Creative Tools for Ad Creative generation and analysis.

This module provides Agent Custom Tools for creative-related operations:
- generate_image_tool: Generate ad images using Gemini Imagen or Bedrock
- generate_video_tool: Generate ad videos using Gemini Veo or Bedrock
- analyze_creative_tool: Analyze creative quality using Gemini Vision
- extract_product_info_tool: Extract product information using Gemini

These tools can call LLMs (Gemini/Bedrock) for AI capabilities.
They call the module functions directly (not through capability.py).
"""

import asyncio
import base64
import structlog
from typing import Any

from app.services.gemini_client import GeminiClient, GeminiError
from app.services.s3_client import S3Client, S3Error, get_s3_client
from app.services.mcp_client import MCPClient, MCPError
from app.services.bedrock_image_client import BedrockImageClient
from app.services.bedrock_video_client import BedrockVideoClient
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
            context: Execution context with user_id and model_preferences

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

        # Get user's model preferences from context (default to gemini)
        model_preferences = context.get("model_preferences") if context else None
        image_provider = "gemini"
        image_model = "gemini-2.5-flash-image"

        if model_preferences:
            # Extract image generation preferences
            if hasattr(model_preferences, "image_generation_provider"):
                image_provider = model_preferences.image_generation_provider
                image_model = model_preferences.image_generation_model
            elif isinstance(model_preferences, dict):
                image_provider = model_preferences.get("image_generation_provider", "gemini")
                image_model = model_preferences.get("image_generation_model", "gemini-2.5-flash-image")

        log = logger.bind(
            tool=self.name,
            user_id=user_id,
            style=style,
            aspect_ratio=aspect_ratio,
            count=count,
            image_provider=image_provider,
            image_model=image_model,
        )
        log.info("generate_image_start")

        try:
            # Handle product_info - it can be a string, JSON string, or dict
            if isinstance(product_info, str):
                # Try to parse as JSON first
                try:
                    import json
                    product_info_dict = json.loads(product_info)
                    # If it's a dict with "prompt" key, use that directly as the image prompt
                    if isinstance(product_info_dict, dict) and "prompt" in product_info_dict:
                        prompt = product_info_dict["prompt"]
                    elif isinstance(product_info_dict, dict) and "product_info" in product_info_dict:
                        # Nested structure: {"product_info": "description"}
                        prompt = str(product_info_dict["product_info"])
                    else:
                        # Use the dict for _build_image_prompt
                        product_info = product_info_dict
                        prompt = self._build_image_prompt(product_info, style)
                except (json.JSONDecodeError, ValueError):
                    # Not JSON, treat as plain text description
                    prompt = product_info
            elif isinstance(product_info, dict):
                # Already a dict, use _build_image_prompt
                prompt = self._build_image_prompt(product_info, style)
            else:
                # Fallback: convert to string
                prompt = str(product_info)

            log.info("generating_image", prompt_preview=prompt[:100])

            # Generate images using user-selected provider
            if image_provider == "gemini":
                image_bytes_list = await self.gemini_client.generate_images(
                    prompt=prompt,
                    count=count,
                    aspect_ratio=aspect_ratio,
                    use_pro_model="pro" in image_model.lower(),
                )
            elif image_provider == "bedrock":
                # Use Bedrock for image generation
                # Note: AI Agent should provide prompt in English (system prompt instructs this)
                bedrock_client = BedrockImageClient()

                # Convert aspect ratio to width/height
                aspect_map = {
                    "1:1": (1024, 1024),
                    "16:9": (1024, 576),
                    "9:16": (576, 1024),
                    "4:3": (1024, 768),
                    "3:4": (768, 1024),
                }
                width, height = aspect_map.get(aspect_ratio, (1024, 1024))

                image_bytes_list = await bedrock_client.generate_images(
                    prompt=prompt,
                    model_id=image_model,
                    count=count,
                    width=width,
                    height=height,
                )
            elif image_provider == "sagemaker":
                # SageMaker support not implemented yet
                log.warning(
                    "unsupported_image_provider_fallback",
                    requested_provider=image_provider,
                    fallback="gemini"
                )
                image_bytes_list = await self.gemini_client.generate_images(
                    prompt=prompt,
                    count=count,
                    aspect_ratio=aspect_ratio,
                    use_pro_model=False,
                )
            else:
                # Fallback to Gemini for unknown providers
                log.warning(
                    "unknown_image_provider_fallback",
                    requested_provider=image_provider,
                    fallback="gemini"
                )
                image_bytes_list = await self.gemini_client.generate_images(
                    prompt=prompt,
                    count=count,
                    aspect_ratio=aspect_ratio,
                    use_pro_model=False,
                )

            log.info("images_generated", count=len(image_bytes_list))

            # Upload images to S3 for persistent storage (not base64 in DB)
            # This follows the requirement: 图片存储到对象存储，前端通过签名URL访问
            s3_client = get_s3_client()
            creative_ids = []
            image_objects = []  # S3 object info for frontend to fetch signed URLs

            for idx, image_bytes in enumerate(image_bytes_list):
                # Handle product_info being string or dict
                if isinstance(product_info, dict):
                    product_name = product_info.get("name", "generated_image")
                else:
                    product_name = "generated_image"
                filename = f"{product_name}_{style}_{idx + 1}.png"

                try:
                    # Upload to S3
                    upload_result = await s3_client.upload_for_chat_display(
                        image_bytes=image_bytes,
                        filename=filename,
                        user_id=user_id or "anonymous",
                        session_id=context.get("session_id", "unknown") if context else "unknown",
                        style=style,
                    )

                    # Return as attachment (unified format)
                    image_objects.append({
                        "id": f"image_{idx}_{upload_result['object_name'].split('/')[-1].split('.')[0]}",
                        "filename": filename,
                        "contentType": "image/png",
                        "size": len(image_bytes),
                        "s3Url": upload_result["object_name"],  # S3 object key for fetching presigned URL
                        "type": "image",
                    })

                    log.info(
                        "image_uploaded_to_s3",
                        index=idx,
                        object_name=upload_result["object_name"],
                    )

                except S3Error as e:
                    log.warning(
                        "s3_upload_failed",
                        index=idx,
                        error=str(e),
                    )
                    # Fallback: include base64 only if GCS fails
                    image_b64 = base64.b64encode(image_bytes).decode("utf-8")
                    image_objects.append({
                        "index": idx,
                        "format": "png",
                        "size": len(image_bytes),
                        "data_b64": image_b64,  # Fallback only
                    })

                # Try to save creative record via MCP
                try:
                    result = await self.mcp_client.call_tool(
                        "save_creative",
                        {
                            "user_id": user_id,
                            "gcs_object_name": image_objects[-1].get("object_name"),
                            "metadata": {
                                "product_name": product_name,
                                "style": style,
                                "aspect_ratio": aspect_ratio,
                                "generated_by": "gemini_imagen",
                                "prompt": prompt,
                            },
                        },
                    )
                    creative_ids.append(result.get("creative_id"))
                except MCPError as e:
                    log.warning("save_creative_record_failed", index=idx, error=str(e))
                    creative_ids.append(None)

            log.info(
                "generate_image_complete",
                generated=len(image_bytes_list),
                uploaded_to_gcs=len([obj for obj in image_objects if obj.get("object_name")]),
            )

            return {
                "success": True,
                "creative_ids": [cid for cid in creative_ids if cid],
                "count": len(image_bytes_list),
                "attachments": image_objects,  # Unified attachment format
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
    Supports text-to-video, image-to-video (with first frame), and interpolation.
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
                "Generate advertising videos using AI with Veo 3.1. "
                "Supports multiple intelligent modes:\n\n"
                "**Mode 1: Text-to-Video**\n"
                "- Provide product_info or direct prompt\n"
                "- Best for: Creating videos from scratch\n\n"
                "**Mode 2: Image-to-Video (Animate Image)**\n"
                "- Set use_context_image=true to animate the most recent image from chat\n"
                "- Or provide first_frame_b64 directly\n"
                "- Best for: Bringing static images to life\n\n"
                "**Mode 3: Interpolation (First + Last Frame)**\n"
                "- Provide both first_frame_b64 and last_frame_b64\n"
                "- Veo creates smooth transition between frames\n"
                "- Best for: Creating specific start-to-end animations\n\n"
                "**Mode 4: Reference-Guided Generation**\n"
                "- Provide reference_images_b64 (up to 3 images)\n"
                "- Preserves subject appearance from reference images\n"
                "- Best for: Maintaining brand consistency, character appearance\n\n"
                "**Smart Context Usage:**\n"
                "- If user says 'animate this image' or 'make a video from that', set use_context_image=true\n"
                "- If user uploaded images, they're available in conversation history\n"
                "- If user generated images earlier, they're also available\n"
                "- Use context_image_index to select which image (0=most recent)"
            ),
            category=ToolCategory.AGENT_CUSTOM,
            parameters=[
                ToolParameter(
                    name="product_info",
                    type="object",
                    description="Product information including name, description, features. Optional if using image input.",
                    required=False,
                ),
                ToolParameter(
                    name="prompt",
                    type="string",
                    description="Direct text prompt for video generation. Use this for more control over the output.",
                    required=False,
                ),
                ToolParameter(
                    name="style",
                    type="string",
                    description="Video style and mood",
                    required=False,
                    default="dynamic",
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
                ToolParameter(
                    name="first_frame_b64",
                    type="string",
                    description="Base64-encoded image to use as the first frame (image-to-video mode)",
                    required=False,
                ),
                ToolParameter(
                    name="last_frame_b64",
                    type="string",
                    description="Base64-encoded image to use as the last frame (interpolation mode)",
                    required=False,
                ),
                ToolParameter(
                    name="reference_images_b64",
                    type="array",
                    description="Array of base64-encoded reference images for style guidance (max 3)",
                    required=False,
                ),
                ToolParameter(
                    name="use_context_image",
                    type="boolean",
                    description="If true, use the most recent image from conversation history as first_frame",
                    required=False,
                    default=False,
                ),
                ToolParameter(
                    name="context_image_index",
                    type="number",
                    description="Index of the image to use from conversation history (0 = most recent)",
                    required=False,
                    default=0,
                ),
                ToolParameter(
                    name="negative_prompt",
                    type="string",
                    description="Things to avoid in the video",
                    required=False,
                ),
            ],
            returns="object with video URL/data once generation completes",
            credit_cost=20.0,
            tags=["creative", "video", "generation", "ai", "image-to-video"],
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
            context: Execution context with user_id, conversation_history, and model_preferences

        Returns:
            Video URL and metadata once generation completes

        Raises:
            ToolExecutionError: If generation fails
        """
        import asyncio

        user_id = context.get("user_id") if context else None
        product_info = parameters.get("product_info", {})
        direct_prompt = parameters.get("prompt")
        style = parameters.get("style", "dynamic")
        duration = parameters.get("duration", 4)
        aspect_ratio = parameters.get("aspect_ratio", "16:9")
        negative_prompt = parameters.get("negative_prompt")

        # Image inputs
        first_frame_b64 = parameters.get("first_frame_b64")
        last_frame_b64 = parameters.get("last_frame_b64")
        reference_images_b64 = parameters.get("reference_images_b64", [])
        use_context_image = parameters.get("use_context_image", False)
        context_image_index = parameters.get("context_image_index", 0)

        # Get user's model preferences from context (default to gemini)
        model_preferences = context.get("model_preferences") if context else None
        video_provider = "gemini"
        video_model = "gemini-veo-3.1"

        if model_preferences:
            # Extract video generation preferences
            if hasattr(model_preferences, "video_generation_provider"):
                video_provider = model_preferences.video_generation_provider
                video_model = model_preferences.video_generation_model
            elif isinstance(model_preferences, dict):
                video_provider = model_preferences.get("video_generation_provider", "gemini")
                video_model = model_preferences.get("video_generation_model", "gemini-veo-3.1")

        log = logger.bind(
            tool=self.name,
            user_id=user_id,
            style=style,
            duration=duration,
            aspect_ratio=aspect_ratio,
            has_first_frame=first_frame_b64 is not None,
            has_last_frame=last_frame_b64 is not None,
            use_context_image=use_context_image,
            video_provider=video_provider,
            video_model=video_model,
        )
        log.info("generate_video_start")

        try:
            # Extract image from conversation history if requested
            if use_context_image and not first_frame_b64:
                context_image = self._extract_image_from_context(context, context_image_index)
                if context_image:
                    first_frame_b64 = context_image
                    log.info("using_context_image", index=context_image_index)
                else:
                    log.warning("no_context_image_found")

            # Convert base64 to bytes
            first_frame = base64.b64decode(first_frame_b64) if first_frame_b64 else None
            last_frame = base64.b64decode(last_frame_b64) if last_frame_b64 else None
            reference_images = [
                base64.b64decode(img) for img in reference_images_b64[:3]
            ] if reference_images_b64 else None

            # Build generation prompt
            if direct_prompt:
                prompt = direct_prompt
            elif first_frame and not product_info:
                # Image-to-video mode without product info
                prompt = self._build_image_animation_prompt(style)
            else:
                prompt = self._build_video_prompt(product_info, style)

            log.info("generating_video",
                     prompt_preview=prompt[:100],
                     mode="image-to-video" if first_frame else "text-to-video")

            # Generate video using user-selected provider
            if video_provider == "gemini":
                result = await self.gemini_client.generate_video(
                    prompt=prompt,
                    duration=duration,
                    aspect_ratio=aspect_ratio,
                    first_frame=first_frame,
                    last_frame=last_frame,
                    reference_images=reference_images,
                    negative_prompt=negative_prompt,
                    use_fast_model="fast" in video_model.lower(),
                )
            elif video_provider == "bedrock":
                # Use Bedrock for video generation
                # Note: AI Agent should provide prompt in English (system prompt instructs this)
                bedrock_client = BedrockVideoClient()

                result = await bedrock_client.generate_video(
                    prompt=prompt,
                    model_id=video_model,
                    duration=duration,
                    aspect_ratio=aspect_ratio,
                    first_frame=first_frame,
                    last_frame=last_frame,
                    negative_prompt=negative_prompt,
                    user_id=user_id or "anonymous",
                )
            elif video_provider == "sagemaker":
                # SageMaker support not implemented yet
                log.warning(
                    "unsupported_video_provider_fallback",
                    requested_provider=video_provider,
                    fallback="gemini"
                )
                result = await self.gemini_client.generate_video(
                    prompt=prompt,
                    duration=duration,
                    aspect_ratio=aspect_ratio,
                    first_frame=first_frame,
                    last_frame=last_frame,
                    reference_images=reference_images,
                    negative_prompt=negative_prompt,
                    use_fast_model=False,
                )
            else:
                # Fallback to Gemini for unknown providers
                log.warning(
                    "unknown_video_provider_fallback",
                    requested_provider=video_provider,
                    fallback="gemini"
                )
                result = await self.gemini_client.generate_video(
                    prompt=prompt,
                    duration=duration,
                    aspect_ratio=aspect_ratio,
                    first_frame=first_frame,
                    last_frame=last_frame,
                    reference_images=reference_images,
                    negative_prompt=negative_prompt,
                    use_fast_model=False,
                )

            # Check if video is already completed (for synchronous providers like Bedrock)
            if result.get("status") == "completed":
                video_bytes = result.get("video_bytes")
                video_data_b64 = result.get("video_data_b64")
                operation_id = result.get("operation_id", f"sync_{int(asyncio.get_event_loop().time())}")

                log.info(
                    "video_generation_complete_sync",
                    operation_id=operation_id,
                    has_video_bytes=video_bytes is not None,
                )

                final_result = {
                    "success": True,
                    "status": "completed",
                    "operation_id": operation_id,
                    "message": "Video generated successfully",
                }

                # Upload video to S3 for persistent public access
                if video_bytes:
                    try:
                        s3_client = get_s3_client()
                        product_name = product_info.get("name", "video")
                        filename = f"{product_name}_{style}_{operation_id[-8:]}.mp4"

                        upload_result = await s3_client.upload_video(
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

                        # Return video as attachment (frontend will fetch presigned URL)
                        final_result["attachments"] = [{
                            "id": f"video_{operation_id[-8:]}",
                            "filename": filename,
                            "contentType": "video/mp4",
                            "size": upload_result["size"],
                            "s3Url": upload_result["object_name"],  # S3 object key for fetching presigned URL
                            "type": "video",
                        }]
                        log.info(
                            "video_uploaded_to_s3",
                            object_name=upload_result["object_name"],
                            size=upload_result["size"],
                        )
                    except S3Error as e:
                        log.warning("s3_upload_failed", error=str(e))
                        # Fallback to base64 if GCS upload fails
                        if video_data_b64:
                            final_result["video_data_b64"] = video_data_b64
                            final_result["video_format"] = "mp4"

                return final_result

            # For async providers (Gemini and Bedrock), poll for completion
            # Bedrock uses invocation_arn, others use operation_id
            operation_id = result.get("operation_id") or result.get("invocation_arn")
            invocation_arn = result.get("invocation_arn")

            log.info("video_generation_started_async", operation_id=operation_id)

            # Poll for completion (max 10 minutes with 10 second intervals for Bedrock video)
            max_attempts = 60 if video_provider != "bedrock" else 60  # 10 min for Bedrock
            poll_interval = 5 if video_provider != "bedrock" else 10  # 10s for Bedrock

            for attempt in range(max_attempts):
                # Use appropriate polling based on provider
                if video_provider == "bedrock":
                    bedrock_client = BedrockVideoClient()
                    poll_result = await bedrock_client.poll_video_operation(invocation_arn, video_model)
                else:
                    poll_result = await self.gemini_client.poll_video_operation(operation_id)

                if poll_result.get("status") == "completed":
                    video_uri = poll_result.get("video_uri")
                    video_bytes = poll_result.get("video_bytes")
                    s3_uri = poll_result.get("s3_uri")

                    # For Bedrock, download video from S3
                    if video_provider == "bedrock" and s3_uri and not video_bytes:
                        try:
                            import boto3
                            # Parse S3 URI: s3://bucket/path/to/file.mp4
                            if s3_uri.startswith("s3://"):
                                s3_parts = s3_uri[5:].split("/", 1)
                                bucket = s3_parts[0]
                                key = s3_parts[1]

                                # List objects to find the actual video file
                                s3_client_boto = boto3.client("s3")
                                response = s3_client_boto.list_objects_v2(
                                    Bucket=bucket,
                                    Prefix=key,
                                )

                                # Find the .mp4 file
                                for obj in response.get("Contents", []):
                                    if obj["Key"].endswith(".mp4"):
                                        # Download the video
                                        obj_response = s3_client_boto.get_object(
                                            Bucket=bucket,
                                            Key=obj["Key"],
                                        )
                                        video_bytes = obj_response["Body"].read()
                                        log.info(
                                            "bedrock_video_downloaded_from_s3",
                                            bucket=bucket,
                                            key=obj["Key"],
                                            size=len(video_bytes),
                                        )
                                        break
                        except Exception as e:
                            log.error("failed_to_download_bedrock_video", error=str(e))

                    log.info(
                        "video_generation_complete",
                        operation_id=operation_id,
                        video_uri=video_uri[:100] if video_uri else None,
                        s3_uri=s3_uri[:100] if s3_uri else None,
                        has_video_bytes=video_bytes is not None,
                    )

                    result = {
                        "success": True,
                        "status": "completed",
                        "operation_id": operation_id,
                        "message": "Video generated successfully",
                    }

                    # Upload video to S3 for persistent public access
                    if video_bytes:
                        try:
                            s3_client = get_s3_client()
                            product_name = product_info.get("name", "video")
                            filename = f"{product_name}_{style}_{operation_id[-8:]}.mp4"

                            upload_result = await s3_client.upload_video(
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

                            # Return video as attachment (frontend will fetch presigned URL)
                            result["attachments"] = [{
                                "id": f"video_{operation_id[-8:]}",
                                "filename": filename,
                                "contentType": "video/mp4",
                                "size": upload_result["size"],
                                "s3Url": upload_result["object_name"],  # S3 object key for fetching presigned URL
                                "type": "video",
                            }]
                            log.info(
                                "video_uploaded_to_s3",
                                object_name=upload_result["object_name"],
                                size=upload_result["size"],
                            )
                        except S3Error as e:
                            log.warning(
                                "s3_upload_failed",
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

    def _extract_image_from_context(
        self,
        context: dict[str, Any] | None,
        index: int = 0,
    ) -> str | None:
        """Extract image from conversation history.

        Args:
            context: Execution context with conversation_history
            index: Index of image to extract (0 = most recent)

        Returns:
            Base64-encoded image data or None
        """
        if not context:
            return None

        conversation_history = context.get("conversation_history", [])
        images_found = []

        # Search through conversation history for images
        for message in reversed(conversation_history):
            # Check for generated images in message
            generated_images = message.get("generated_images", [])
            for img in generated_images:
                if img.get("data_b64"):
                    images_found.append(img["data_b64"])

            # Check for uploaded images (attachments)
            attachments = message.get("attachments", [])
            for att in attachments:
                if att.get("type") == "image" and att.get("data_b64"):
                    images_found.append(att["data_b64"])

            # Check for image URLs that might have been uploaded
            content = message.get("content", "")
            if isinstance(content, str) and "data:image" in content:
                # Extract base64 from data URL
                import re
                match = re.search(r'data:image/[^;]+;base64,([A-Za-z0-9+/=]+)', content)
                if match:
                    images_found.append(match.group(1))

        if images_found and index < len(images_found):
            return images_found[index]

        return None

    def _build_image_animation_prompt(self, style: str) -> str:
        """Build prompt for animating an image.

        Args:
            style: Animation style

        Returns:
            Animation prompt
        """
        style_prompts = {
            "dynamic": "Add dynamic camera movement, zoom effects, and energetic motion",
            "calm": "Add gentle, smooth camera movement with subtle parallax effects",
            "energetic": "Add exciting motion, quick zooms, and vibrant energy",
            "professional": "Add subtle professional camera movement, smooth transitions",
            "lifestyle": "Add natural, organic movement as if capturing a real moment",
        }

        style_desc = style_prompts.get(style, "professional camera movement")

        return f"""Animate this image with {style_desc}.

Requirements:
- Maintain the original image quality and composition
- Add natural, realistic motion
- Create smooth, professional animation
- Suitable for advertising use
- No text overlays or watermarks"""

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


class ExtractProductImagesTool(AgentTool):
    """Tool for extracting product images from e-commerce URLs.

    This tool extracts product images from various e-commerce platforms
    including Shopify, Amazon, and generic websites.
    """

    def __init__(self):
        """Initialize the extract product images tool."""
        metadata = ToolMetadata(
            name="extract_product_images_tool",
            description=(
                "Extract product images from e-commerce URLs. "
                "Supports Shopify, Amazon, and generic websites. "
                "Returns a list of product image URLs that can be used for landing pages."
            ),
            category=ToolCategory.AGENT_CUSTOM,
            parameters=[
                ToolParameter(
                    name="product_url",
                    type="string",
                    description="Product page URL (Shopify, Amazon, or other e-commerce site)",
                    required=True,
                ),
                ToolParameter(
                    name="max_images",
                    type="number",
                    description="Maximum number of images to extract (default: 5)",
                    required=False,
                    default=5,
                ),
            ],
            returns="object with list of product image URLs and platform info",
            credit_cost=1.0,
            tags=["product", "images", "extraction", "scraping"],
        )

        super().__init__(metadata)

    async def execute(
        self,
        parameters: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute product image extraction.

        Args:
            parameters: Tool parameters
            context: Execution context

        Returns:
            List of product image URLs

        Raises:
            ToolExecutionError: If extraction fails
        """
        import httpx
        import re
        import json
        from urllib.parse import urljoin, urlparse

        product_url = parameters.get("product_url")
        max_images = parameters.get("max_images", 5)

        log = logger.bind(
            tool=self.name,
            product_url=product_url,
            max_images=max_images,
        )
        log.info("extract_product_images_start")

        if not product_url:
            raise ToolExecutionError(
                message="product_url is required",
                tool_name=self.name,
                error_code="INVALID_PARAMS",
            )

        try:
            # Detect platform
            platform = self._detect_platform(product_url)
            log.info("platform_detected", platform=platform)

            # Fetch page HTML
            async with httpx.AsyncClient(
                timeout=30.0,
                follow_redirects=True,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                },
            ) as client:
                response = await client.get(product_url)
                response.raise_for_status()
                html = response.text

            # Extract images based on platform
            if platform == "shopify":
                images = self._extract_shopify_images(html, product_url, max_images)
            elif platform == "amazon":
                images = self._extract_amazon_images(html, product_url, max_images)
            else:
                images = self._extract_generic_images(html, product_url, max_images)

            log.info("extract_product_images_complete", image_count=len(images))

            return {
                "success": True,
                "images": images,
                "platform": platform,
                "count": len(images),
                "message": f"Extracted {len(images)} product images from {platform}",
            }

        except httpx.HTTPError as e:
            log.error("http_error", error=str(e))
            raise ToolExecutionError(
                message=f"Failed to fetch URL: {str(e)}",
                tool_name=self.name,
                error_code="HTTP_ERROR",
            )

        except Exception as e:
            log.error("unexpected_error", error=str(e), exc_info=True)
            raise ToolExecutionError(
                message=f"Unexpected error: {str(e)}",
                tool_name=self.name,
            )

    def _detect_platform(self, url: str) -> str:
        """Detect e-commerce platform from URL.

        Args:
            url: Product URL

        Returns:
            Platform identifier: 'shopify', 'amazon', or 'generic'
        """
        url_lower = url.lower()

        # Shopify detection
        if any(
            pattern in url_lower
            for pattern in [
                "myshopify.com",
                ".myshopify.",
                "/products/",
                "cdn.shopify.com",
            ]
        ):
            return "shopify"

        # Amazon detection
        if any(
            pattern in url_lower
            for pattern in [
                "amazon.com",
                "amazon.cn",
                "amazon.co.",
                "amazon.de",
                "amazon.fr",
                "amazon.es",
                "amazon.it",
                "amzn.to",
                "amzn.asia",
            ]
        ):
            return "amazon"

        return "generic"

    def _extract_shopify_images(
        self, html: str, base_url: str, max_images: int
    ) -> list[dict[str, Any]]:
        """Extract images from Shopify product page.

        Args:
            html: Page HTML content
            base_url: Base URL for resolving relative URLs
            max_images: Maximum images to extract

        Returns:
            List of image objects with url and alt
        """
        import re
        import json
        from urllib.parse import urljoin

        images = []
        seen_urls = set()

        # Method 1: Extract from JSON-LD structured data
        json_ld_pattern = r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>'
        for match in re.finditer(json_ld_pattern, html, re.DOTALL | re.IGNORECASE):
            try:
                data = json.loads(match.group(1))
                if isinstance(data, dict):
                    # Single product
                    if data.get("@type") == "Product" and data.get("image"):
                        img_data = data["image"]
                        if isinstance(img_data, str):
                            img_data = [img_data]
                        elif isinstance(img_data, dict):
                            img_data = [img_data.get("url", "")]
                        for img_url in img_data:
                            if img_url and img_url not in seen_urls:
                                seen_urls.add(img_url)
                                images.append({"url": img_url, "alt": data.get("name", "Product")})
            except json.JSONDecodeError:
                continue

        # Method 2: Extract from og:image meta tags
        og_pattern = r'<meta[^>]*property="og:image"[^>]*content="([^"]+)"'
        for match in re.finditer(og_pattern, html, re.IGNORECASE):
            img_url = match.group(1)
            if img_url and img_url not in seen_urls:
                seen_urls.add(img_url)
                images.append({"url": img_url, "alt": "Product Image"})

        # Method 3: Extract from product gallery images (common Shopify patterns)
        gallery_patterns = [
            r'data-zoom="([^"]+)"',
            r'data-src="(https://cdn\.shopify\.com/[^"]+)"',
            r'src="(https://cdn\.shopify\.com/s/files/[^"]+\.(?:jpg|jpeg|png|webp))"',
            r'"featured_image":"([^"]+)"',
        ]
        for pattern in gallery_patterns:
            for match in re.finditer(pattern, html):
                img_url = match.group(1).replace("\\u002F", "/")
                if img_url and img_url not in seen_urls:
                    # Upgrade to larger image size
                    img_url = re.sub(r'_\d+x\d*\.', '_1024x.', img_url)
                    seen_urls.add(img_url)
                    images.append({"url": img_url, "alt": "Product Image"})

        return images[:max_images]

    def _extract_amazon_images(
        self, html: str, base_url: str, max_images: int
    ) -> list[dict[str, Any]]:
        """Extract images from Amazon product page.

        Args:
            html: Page HTML content
            base_url: Base URL for resolving relative URLs
            max_images: Maximum images to extract

        Returns:
            List of image objects with url and alt
        """
        import re
        import json

        images = []
        seen_urls = set()

        # Method 1: Extract from image data JSON
        image_data_pattern = r"'colorImages':\s*\{[^}]*'initial':\s*(\[[^\]]+\])"
        match = re.search(image_data_pattern, html)
        if match:
            try:
                # Clean up the JSON string
                json_str = match.group(1).replace("'", '"')
                img_array = json.loads(json_str)
                for img in img_array:
                    if isinstance(img, dict):
                        # Get hiRes or large image
                        img_url = img.get("hiRes") or img.get("large")
                        if img_url and img_url not in seen_urls:
                            seen_urls.add(img_url)
                            images.append({"url": img_url, "alt": "Product Image"})
            except (json.JSONDecodeError, AttributeError):
                pass

        # Method 2: Extract from landing image
        landing_pattern = r'id="landingImage"[^>]*src="([^"]+)"'
        match = re.search(landing_pattern, html)
        if match:
            img_url = match.group(1)
            if img_url and img_url not in seen_urls:
                # Try to get higher resolution
                img_url = re.sub(r'\._[A-Z]{2}\d+_\.', '._SL1500_.', img_url)
                seen_urls.add(img_url)
                images.append({"url": img_url, "alt": "Product Image"})

        # Method 3: Extract from image gallery data
        gallery_pattern = r'"large":"(https://[^"]+images-amazon\.com[^"]+)"'
        for match in re.finditer(gallery_pattern, html):
            img_url = match.group(1)
            if img_url and img_url not in seen_urls:
                seen_urls.add(img_url)
                images.append({"url": img_url, "alt": "Product Image"})

        # Method 4: og:image fallback
        og_pattern = r'<meta[^>]*property="og:image"[^>]*content="([^"]+)"'
        match = re.search(og_pattern, html, re.IGNORECASE)
        if match:
            img_url = match.group(1)
            if img_url and img_url not in seen_urls:
                seen_urls.add(img_url)
                images.append({"url": img_url, "alt": "Product Image"})

        return images[:max_images]

    def _extract_generic_images(
        self, html: str, base_url: str, max_images: int
    ) -> list[dict[str, Any]]:
        """Extract images from generic e-commerce page.

        Args:
            html: Page HTML content
            base_url: Base URL for resolving relative URLs
            max_images: Maximum images to extract

        Returns:
            List of image objects with url and alt
        """
        import re
        from urllib.parse import urljoin

        images = []
        seen_urls = set()

        # Method 1: og:image (most reliable for product pages)
        og_pattern = r'<meta[^>]*property="og:image"[^>]*content="([^"]+)"'
        for match in re.finditer(og_pattern, html, re.IGNORECASE):
            img_url = match.group(1)
            if img_url:
                img_url = urljoin(base_url, img_url)
                if img_url not in seen_urls:
                    seen_urls.add(img_url)
                    images.append({"url": img_url, "alt": "Product Image"})

        # Method 2: twitter:image
        twitter_pattern = r'<meta[^>]*name="twitter:image"[^>]*content="([^"]+)"'
        for match in re.finditer(twitter_pattern, html, re.IGNORECASE):
            img_url = match.group(1)
            if img_url:
                img_url = urljoin(base_url, img_url)
                if img_url not in seen_urls:
                    seen_urls.add(img_url)
                    images.append({"url": img_url, "alt": "Product Image"})

        # Method 3: Large images from img tags (likely product images)
        img_pattern = r'<img[^>]*src="([^"]+)"[^>]*>'
        for match in re.finditer(img_pattern, html, re.IGNORECASE):
            img_tag = match.group(0)
            img_url = match.group(1)

            if not img_url:
                continue

            # Skip small images, icons, logos
            skip_patterns = ["logo", "icon", "sprite", "button", "pixel", "tracking", "1x1"]
            if any(pattern in img_url.lower() for pattern in skip_patterns):
                continue

            # Check for product-related class or id
            product_indicators = ["product", "gallery", "main", "featured", "hero"]
            is_product_image = any(ind in img_tag.lower() for ind in product_indicators)

            img_url = urljoin(base_url, img_url)
            if img_url not in seen_urls and (is_product_image or len(images) < 2):
                seen_urls.add(img_url)
                # Try to extract alt text
                alt_match = re.search(r'alt="([^"]*)"', img_tag, re.IGNORECASE)
                alt_text = alt_match.group(1) if alt_match else "Product Image"
                images.append({"url": img_url, "alt": alt_text})

        return images[:max_images]


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
        ExtractProductImagesTool(),
    ]
