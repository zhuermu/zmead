"""AWS Bedrock Image Generation Client.

Supports multiple image generation models:
- Amazon Nova Canvas (amazon.nova-canvas-v1:0)
- Stable Diffusion XL (stability.stable-diffusion-xl-v1)
- Stable Diffusion 3 Large (stability.sd3-large-v1:0)
- Stable Image Ultra (stability.stable-image-ultra-v1:0)
- Stable Image Core (stability.stable-image-core-v1:0)
- Amazon Titan Image Generator v2 (amazon.titan-image-generator-v2:0)
"""

import base64
import json
from typing import Any

import boto3
import structlog
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import get_settings

logger = structlog.get_logger(__name__)


class BedrockImageClient:
    """AWS Bedrock image generation client."""

    def __init__(
        self,
        region: str | None = None,
    ):
        """Initialize Bedrock image client.

        Args:
            region: AWS region (defaults to BEDROCK_REGION)
        """
        settings = get_settings()
        # Use BEDROCK_REGION for Bedrock models
        self.default_region = region or settings.bedrock_region
        self._client = None  # Will be initialized per-request based on model

        logger.info(
            "bedrock_image_client_initialized",
            default_region=self.default_region,
        )

    def _get_client_for_model(self, model_id: str):
        """Get Bedrock client for specific model with appropriate region.

        Args:
            model_id: Model identifier

        Returns:
            Bedrock runtime client
        """
        # Nova Canvas models require us-east-1
        if "nova-canvas" in model_id:
            region = "us-east-1"
        else:
            # All other models use default region (us-west-2)
            region = self.default_region

        try:
            client = boto3.client(
                service_name="bedrock-runtime",
                region_name=region,
            )
            logger.info(
                "bedrock_client_created",
                model_id=model_id,
                region=region,
            )
            return client
        except Exception as e:
            logger.error("bedrock_client_creation_failed", model_id=model_id, region=region, error=str(e))
            raise RuntimeError(f"Failed to create Bedrock client: {e}")

    async def generate_images(
        self,
        prompt: str,
        model_id: str = "amazon.nova-canvas-v1:0",
        count: int = 1,
        width: int = 1024,
        height: int = 1024,
        negative_prompt: str | None = None,
        **kwargs: Any,
    ) -> list[bytes]:
        """Generate images using Bedrock.

        Args:
            prompt: Text prompt for image generation
            model_id: Bedrock model ID
            count: Number of images to generate (1-5)
            width: Image width in pixels
            height: Image height in pixels
            negative_prompt: Things to avoid in the image
            **kwargs: Additional model-specific parameters

        Returns:
            List of image bytes

        Raises:
            RuntimeError: If generation fails
        """
        log = logger.bind(
            model_id=model_id,
            prompt_preview=prompt[:100],
            count=count,
            width=width,
            height=height,
        )
        log.info("bedrock_image_generation_start")

        try:
            # Get appropriate client for this model
            client = self._get_client_for_model(model_id)

            # Prepare request based on model family
            if "nova-canvas" in model_id:
                body = self._build_nova_canvas_request(
                    prompt, count, width, height, negative_prompt, **kwargs
                )
            elif "stability" in model_id:
                body = self._build_stability_request(
                    prompt, count, width, height, negative_prompt, model_id, **kwargs
                )
            elif "titan-image" in model_id:
                body = self._build_titan_request(
                    prompt, count, width, height, negative_prompt, **kwargs
                )
            else:
                raise ValueError(f"Unsupported model: {model_id}")

            # Invoke model
            response = client.invoke_model(
                modelId=model_id,
                body=json.dumps(body),
                contentType="application/json",
                accept="application/json",
            )

            # Parse response
            response_body = json.loads(response["body"].read())

            # Log response structure for debugging
            log.info(
                "bedrock_response_received",
                model_id=model_id,
                response_keys=list(response_body.keys()),
                response_preview=str(response_body)[:200],
            )

            # Extract images based on model family
            images = []
            if "nova-canvas" in model_id or "titan-image" in model_id:
                # Nova Canvas and Titan return images in "images" array
                for img_data in response_body.get("images", []):
                    image_bytes = base64.b64decode(img_data)
                    images.append(image_bytes)
            elif "stability" in model_id:
                # Stability models may return different formats
                # SD3 returns images array, SDXL returns artifacts
                if "images" in response_body:
                    # SD3 format
                    for img in response_body.get("images", []):
                        if isinstance(img, str):
                            image_bytes = base64.b64decode(img)
                            images.append(image_bytes)
                elif "artifacts" in response_body:
                    # SDXL format
                    for artifact in response_body.get("artifacts", []):
                        if artifact.get("finishReason") == "SUCCESS":
                            image_bytes = base64.b64decode(artifact["base64"])
                            images.append(image_bytes)

            if not images:
                log.error(
                    "no_images_in_response",
                    response_body=response_body,
                )
                raise RuntimeError("No images generated")

            log.info("bedrock_image_generation_complete", generated_count=len(images))
            return images[:count]  # Ensure we don't return more than requested

        except (BotoCoreError, ClientError) as e:
            log.error("bedrock_image_generation_failed", error=str(e))
            raise RuntimeError(f"Bedrock image generation failed: {e}")
        except Exception as e:
            log.error("bedrock_image_unexpected_error", error=str(e))
            raise RuntimeError(f"Unexpected error: {e}")

    def _build_nova_canvas_request(
        self,
        prompt: str,
        count: int,
        width: int,
        height: int,
        negative_prompt: str | None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Build request for Amazon Nova Canvas.

        Args:
            prompt: Generation prompt
            count: Number of images
            width: Image width
            height: Image height
            negative_prompt: Negative prompt
            **kwargs: Additional parameters

        Returns:
            Request body
        """
        body = {
            "taskType": "TEXT_IMAGE",
            "textToImageParams": {
                "text": prompt,
            },
            "imageGenerationConfig": {
                "numberOfImages": count,
                "width": width,
                "height": height,
                "cfgScale": kwargs.get("cfg_scale", 8.0),
                "quality": kwargs.get("quality", "standard"),
            },
        }

        if negative_prompt:
            body["textToImageParams"]["negativeText"] = negative_prompt

        return body

    def _build_stability_request(
        self,
        prompt: str,
        count: int,
        width: int,
        height: int,
        negative_prompt: str | None,
        model_id: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Build request for Stability AI models.

        Args:
            prompt: Generation prompt
            count: Number of images
            width: Image width
            height: Image height
            negative_prompt: Negative prompt
            model_id: Model ID for version detection
            **kwargs: Additional parameters

        Returns:
            Request body
        """
        # Stable Diffusion 3 uses different format
        if "sd3" in model_id:
            # Map width:height to valid aspect ratio
            aspect_ratio_map = {
                (1024, 1024): "1:1",
                (1024, 576): "16:9",
                (576, 1024): "9:16",
                (1344, 768): "16:9",
                (768, 1344): "9:16",
                (1536, 640): "21:9",
                (640, 1536): "9:21",
            }
            aspect_ratio = aspect_ratio_map.get((width, height), "1:1")

            body = {
                "prompt": prompt,
                "mode": "text-to-image",
                "aspect_ratio": aspect_ratio,
                "output_format": "png",
            }
            if negative_prompt:
                body["negative_prompt"] = negative_prompt
        else:
            # SDXL and Stable Image models
            body = {
                "text_prompts": [{"text": prompt, "weight": 1.0}],
                "cfg_scale": kwargs.get("cfg_scale", 7.0),
                "samples": count,
                "steps": kwargs.get("steps", 50),
                "width": width,
                "height": height,
            }
            if negative_prompt:
                body["text_prompts"].append({"text": negative_prompt, "weight": -1.0})

        return body

    def _build_titan_request(
        self,
        prompt: str,
        count: int,
        width: int,
        height: int,
        negative_prompt: str | None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Build request for Amazon Titan Image Generator.

        Args:
            prompt: Generation prompt
            count: Number of images
            width: Image width
            height: Image height
            negative_prompt: Negative prompt
            **kwargs: Additional parameters

        Returns:
            Request body
        """
        body = {
            "taskType": "TEXT_IMAGE",
            "textToImageParams": {
                "text": prompt,
            },
            "imageGenerationConfig": {
                "numberOfImages": count,
                "width": width,
                "height": height,
                "cfgScale": kwargs.get("cfg_scale", 8.0),
                "quality": kwargs.get("quality", "standard"),
            },
        }

        if negative_prompt:
            body["textToImageParams"]["negativeText"] = negative_prompt

        return body


__all__ = ["BedrockImageClient"]
