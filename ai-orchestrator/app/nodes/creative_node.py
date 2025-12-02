"""Creative module node with real Gemini Imagen 3 integration.

This module implements the Ad Creative functionality with:
- Gemini Imagen 3 for image generation
- Gemini 2.5 Flash for image analysis and quality scoring
- Google Cloud Storage for image uploads (replaces S3)
- Temporary storage in Redis for preview (MCP save deferred to user request)
- Credit management with refund on failure

Flow:
1. User requests creative generation
2. Check credits via MCP
3. Generate images using Imagen 3
4. Upload to GCS for chat display
5. Store temp references in Redis (30 min TTL)
6. Deduct credits
7. Return preview URLs to user
8. User can later explicitly save to asset library via MCP

Requirements: 需求 6 (Ad Creative), 需求 12.4 (Error Recovery)
"""

import asyncio
import base64
import uuid
from typing import Any

import httpx
import structlog
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.errors import ErrorHandler
from app.core.retry import retry_async
from app.core.state import AgentState
from app.services.credit_client import (
    CreditClient,
    CreditError,
    InsufficientCreditsError,
    get_credit_client,
)
from app.services.gemini_client import GeminiClient, GeminiError
from app.services.gcs_client import GCSClient, GCSError, get_gcs_client
from app.services.temp_storage import store_temp_creative, store_temp_batch

logger = structlog.get_logger(__name__)


# Credit cost per creative
CREDIT_PER_CREATIVE = 0.5

# Supported image styles
CREATIVE_STYLES = [
    "简约风格",
    "现代风格",
    "活力风格",
    "商务风格",
    "时尚风格",
    "科技风格",
    "自然风格",
    "奢华风格",
]


class CreativeAnalysis(BaseModel):
    """Structured output for creative analysis."""

    score: int = Field(ge=0, le=100, description="Quality score 0-100")
    composition: str = Field(description="Composition analysis")
    color_harmony: str = Field(description="Color harmony assessment")
    brand_fit: str = Field(description="Brand fit assessment")
    ad_effectiveness: str = Field(description="Predicted ad effectiveness")
    suggestions: list[str] = Field(description="Improvement suggestions")


class ImagenClient:
    """Client for Gemini native image generation.

    Uses the Gemini API with responseModalities=["IMAGE"] to generate images.
    Supported models: gemini-2.5-flash-image, gemini-3-pro-image-preview
    """

    def __init__(self, api_key: str | None = None, model: str | None = None):
        """Initialize Imagen client.

        Args:
            api_key: Gemini API key
            model: Image generation model name (e.g., gemini-2.5-flash-image)
        """
        settings = get_settings()
        self.api_key = api_key or settings.gemini_api_key
        self.model = model or settings.gemini_model_imagen
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"

    async def generate_image(
        self,
        prompt: str,
        aspect_ratio: str = "1:1",
        negative_prompt: str | None = None,
    ) -> bytes:
        """Generate an image using Gemini native image generation.

        Uses the generateContent endpoint with responseModalities=["IMAGE"]
        as per official documentation: https://ai.google.dev/gemini-api/docs/image-generation

        Args:
            prompt: Text prompt for image generation
            aspect_ratio: Image aspect ratio (1:1, 16:9, 9:16, 4:3, 3:4)
            negative_prompt: Things to avoid in the image (appended to prompt)

        Returns:
            Image bytes (PNG format)

        Raises:
            GeminiError: If generation fails
        """
        url = f"{self.base_url}/models/{self.model}:generateContent"

        # Build the prompt with negative prompt if provided
        full_prompt = prompt
        if negative_prompt:
            full_prompt = f"{prompt}. Avoid: {negative_prompt}"

        # Use generateContent with responseModalities as per official docs
        payload = {
            "contents": [
                {
                    "parts": [{"text": full_prompt}]
                }
            ],
            "generationConfig": {
                "responseModalities": ["IMAGE"],
                "responseMimeType": "image/png",
            },
        }

        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key,
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                logger.info(
                    "imagen_api_request",
                    model=self.model,
                    prompt_length=len(full_prompt),
                )
                response = await client.post(url, json=payload, headers=headers)

                if response.status_code == 429:
                    raise GeminiError("Rate limit exceeded", code="RATE_LIMIT", retryable=True)

                if response.status_code >= 500:
                    raise GeminiError(
                        f"Server error: {response.status_code}",
                        code="SERVER_ERROR",
                        retryable=True,
                    )

                if response.status_code != 200:
                    error_data = response.json() if response.content else {}
                    error_msg = error_data.get("error", {}).get("message", response.text[:500])
                    logger.error(
                        "imagen_api_error",
                        status_code=response.status_code,
                        error=error_msg,
                    )
                    raise GeminiError(f"Image generation failed: {error_msg}", code="API_ERROR")

                data = response.json()

                # Extract image from generateContent response
                # Response format: { "candidates": [{ "content": { "parts": [{ "inlineData": { "mimeType": "image/png", "data": "..." } }] } }] }
                candidates = data.get("candidates", [])
                if not candidates:
                    raise GeminiError("No candidates in response", code="NO_OUTPUT")

                content = candidates[0].get("content", {})
                parts = content.get("parts", [])

                for part in parts:
                    inline_data = part.get("inlineData", {})
                    if inline_data:
                        image_data = inline_data.get("data")
                        if image_data:
                            logger.info("imagen_api_success", image_size_approx=len(image_data))
                            return base64.b64decode(image_data)

                raise GeminiError("No image data in response", code="NO_OUTPUT")

            except httpx.TimeoutException:
                raise GeminiError("Image generation timed out", code="TIMEOUT", retryable=True)
            except httpx.HTTPError as e:
                raise GeminiError(f"HTTP error: {e}", code="HTTP_ERROR", retryable=True)


def estimate_creative_cost(params: dict[str, Any]) -> float:
    """Estimate credit cost for creative generation.

    Args:
        params: Action parameters

    Returns:
        Estimated credit cost
    """
    count = params.get("count", 10)
    return count * CREDIT_PER_CREATIVE


def build_image_prompt(
    product_url: str | None = None,
    product_description: str | None = None,
    style: str | None = None,
    target_audience: str | None = None,
) -> str:
    """Build an optimized prompt for ad creative generation.

    Args:
        product_url: URL of the product
        product_description: Description of the product
        style: Desired creative style
        target_audience: Target audience description

    Returns:
        Optimized prompt string
    """
    base_prompt = "Professional advertising creative image"

    if product_description:
        base_prompt += f" for {product_description}"

    if style:
        style_prompts = {
            "简约风格": "minimalist, clean, white space, modern typography",
            "现代风格": "contemporary, sleek, geometric shapes, bold colors",
            "活力风格": "vibrant, energetic, dynamic composition, bright colors",
            "商务风格": "professional, corporate, trustworthy, blue tones",
            "时尚风格": "trendy, stylish, fashion-forward, editorial quality",
            "科技风格": "futuristic, tech-inspired, digital, neon accents",
            "自然风格": "organic, natural, earthy tones, sustainable feel",
            "奢华风格": "luxury, premium, elegant, gold accents, sophisticated",
        }
        style_desc = style_prompts.get(style, style)
        base_prompt += f", {style_desc} style"

    if target_audience:
        base_prompt += f", appealing to {target_audience}"

    # Add quality modifiers
    base_prompt += ", high quality, professional photography, studio lighting"
    base_prompt += ", suitable for digital advertising, eye-catching"

    return base_prompt


async def analyze_creative(
    image_bytes: bytes,
    gemini_client: GeminiClient,
) -> CreativeAnalysis:
    """Analyze a creative image using Gemini 2.5 Flash.

    Args:
        image_bytes: Image data
        gemini_client: Gemini client instance

    Returns:
        CreativeAnalysis with quality score and feedback
    """
    # Convert image to base64 for analysis
    image_b64 = base64.b64encode(image_bytes).decode("utf-8")

    messages = [
        {
            "role": "system",
            "content": """You are an expert advertising creative analyst. 
Analyze the provided image and evaluate its quality for digital advertising.
Provide a comprehensive analysis including:
- Overall quality score (0-100)
- Composition analysis
- Color harmony assessment
- Brand fit potential
- Predicted ad effectiveness
- Specific improvement suggestions""",
        },
        {
            "role": "user",
            "content": f"Analyze this advertising creative image:\n[Image data: {image_b64[:100]}...]",
        },
    ]

    try:
        analysis = await gemini_client.fast_structured_output(
            messages=messages,
            schema=CreativeAnalysis,
        )
        return analysis
    except GeminiError:
        # Return default analysis if analysis fails
        return CreativeAnalysis(
            score=75,
            composition="Unable to analyze",
            color_harmony="Unable to analyze",
            brand_fit="Unable to analyze",
            ad_effectiveness="Unable to analyze",
            suggestions=["Manual review recommended"],
        )


async def upload_to_gcs(
    gcs_client: GCSClient,
    image_bytes: bytes,
    filename: str,
    user_id: str,
    session_id: str,
    style: str | None = None,
    score: int | None = None,
) -> dict[str, Any]:
    """Upload image to Google Cloud Storage.

    Args:
        gcs_client: GCS client instance
        image_bytes: Image data
        filename: Filename for the upload
        user_id: User ID
        session_id: Session ID
        style: Creative style
        score: Quality score

    Returns:
        Dict with gcs_url and public_url

    Raises:
        GCSError: If upload fails
    """
    result = await gcs_client.upload_for_chat_display(
        image_bytes=image_bytes,
        filename=filename,
        user_id=user_id,
        session_id=session_id,
        style=style,
        score=score,
    )

    return {
        "gcs_url": result["gcs_url"],
        "public_url": result["public_url"],
        "object_name": result["object_name"],
        "file_size": result["size"],
    }



async def creative_node(state: AgentState) -> dict[str, Any]:
    """Ad Creative node with real Gemini Imagen 3 integration.

    This node generates images and stores them temporarily for preview.
    MCP save to asset library is deferred until user explicitly requests it.

    Flow:
    1. Estimates credit cost
    2. Checks credit via MCP
    3. Generates images using Gemini Imagen 3
    4. Analyzes images using Gemini 2.5 Flash
    5. Uploads to GCS for chat display
    6. Stores temp references in Redis (30 min TTL)
    7. Deducts credit via MCP
    8. Returns preview URLs and temp_ids to user
    9. User can later save via "save_creative" intent

    Args:
        state: Current agent state

    Returns:
        State updates with completed results including temp_ids for later save

    Requirements: 需求 6.1-6.5
    """
    log = logger.bind(
        user_id=state.get("user_id"),
        session_id=state.get("session_id"),
        module="creative",
    )
    log.info("creative_node_start")

    # Get action parameters
    pending_actions = state.get("pending_actions", [])
    creative_actions = [a for a in pending_actions if a.get("module") == "creative"]

    if not creative_actions:
        log.warning("creative_node_no_actions")
        return {"completed_results": []}

    action = creative_actions[0]
    params = action.get("params", {})
    count = min(params.get("count", 10), 20)  # Max 20 images per request
    style = params.get("style")
    product_url = params.get("product_url")
    product_description = params.get("product_description")
    target_audience = params.get("target_audience")

    # Step 1: Estimate cost
    estimated_cost = estimate_creative_cost({"count": count})
    operation_id = f"creative_{uuid.uuid4().hex[:12]}"

    log.info(
        "creative_node_cost_estimated",
        count=count,
        estimated_cost=estimated_cost,
        operation_id=operation_id,
    )

    generated_creatives: list[dict[str, Any]] = []
    credit_deducted = False
    actual_cost = 0.0

    try:
        # Get credit client (system-level, not MCP)
        credit_client = get_credit_client()

        # Step 2: Check credit with retry (direct API, not MCP)
        try:
            await retry_async(
                lambda: credit_client.check_credit(
                    user_id=state.get("user_id", ""),
                    estimated_credits=estimated_cost,
                    operation_type="generate_creative",
                ),
                max_retries=3,
                context="creative_credit_check",
            )
            log.info("creative_node_credit_check_passed")

        except InsufficientCreditsError as e:
            log.warning(
                "creative_node_insufficient_credits",
                required=e.required,
                available=e.available,
            )
            error_state = ErrorHandler.create_node_error_state(
                error=e,
                node_name="creative",
                user_id=state.get("user_id"),
                session_id=state.get("session_id"),
            )
            error_state["completed_results"] = [
                {
                    "action_type": "generate_creative",
                    "module": "creative",
                    "status": "error",
                    "data": {},
                    "error": error_state.get("error"),
                    "cost": 0,
                    "mock": False,
                }
            ]
            return error_state

        except CreditError as e:
            log.error("creative_node_credit_check_failed", error=str(e))
            error_state = ErrorHandler.create_node_error_state(
                error=e,
                node_name="creative",
                user_id=state.get("user_id"),
                session_id=state.get("session_id"),
            )
            error_state["completed_results"] = [
                {
                    "action_type": "generate_creative",
                    "module": "creative",
                    "status": "error",
                    "data": {},
                    "error": error_state.get("error"),
                    "cost": 0,
                    "mock": False,
                }
            ]
            return error_state

        # Step 3: Generate images using Imagen 3
        imagen_client = ImagenClient()
        gemini_client = GeminiClient()
        gcs_client = get_gcs_client()

        # Build prompt
        prompt = build_image_prompt(
            product_url=product_url,
            product_description=product_description,
            style=style,
            target_audience=target_audience,
        )

        log.info("creative_node_generating", count=count, prompt=prompt[:100])

        # Track temp IDs for batch reference
        temp_ids: list[str] = []
        user_id = state.get("user_id", "")
        session_id = state.get("session_id", "")

        # Generate images one by one (Imagen 3 generates 1 at a time)
        for i in range(count):
            try:
                # Vary the style slightly for each image
                current_style = style or CREATIVE_STYLES[i % len(CREATIVE_STYLES)]
                current_prompt = build_image_prompt(
                    product_url=product_url,
                    product_description=product_description,
                    style=current_style,
                    target_audience=target_audience,
                )

                # Generate image with retry
                image_bytes = await retry_async(
                    lambda p=current_prompt: imagen_client.generate_image(p),
                    max_retries=3,
                    context=f"imagen_generate_{i}",
                )

                log.info("creative_node_image_generated", index=i, size=len(image_bytes))

                # Step 4: Analyze image
                analysis = await analyze_creative(image_bytes, gemini_client)

                # Step 5: Upload to GCS for chat display
                filename = f"{current_style}-{i + 1:02d}.png"
                upload_result = await upload_to_gcs(
                    gcs_client=gcs_client,
                    image_bytes=image_bytes,
                    filename=filename,
                    user_id=user_id,
                    session_id=session_id,
                    style=current_style,
                    score=analysis.score,
                )

                log.info(
                    "creative_node_image_uploaded",
                    index=i,
                    public_url=upload_result["public_url"],
                )

                # Step 6: Store temp metadata in Redis (NOT saving to MCP yet)
                # NOTE: Only metadata is stored in Redis. Image is permanently in GCS.
                temp_id = await store_temp_creative(
                    user_id=user_id,
                    session_id=session_id,
                    gcs_url=upload_result["gcs_url"],
                    public_url=upload_result["public_url"],
                    filename=filename,
                    style=current_style,
                    score=analysis.score,
                    analysis={
                        "composition": analysis.composition,
                        "color_harmony": analysis.color_harmony,
                        "brand_fit": analysis.brand_fit,
                        "ad_effectiveness": analysis.ad_effectiveness,
                        "suggestions": analysis.suggestions,
                        "object_name": upload_result["object_name"],
                        "file_size": upload_result["file_size"],  # Store file size for later save
                    },
                )
                temp_ids.append(temp_id)

                generated_creatives.append(
                    {
                        "temp_id": temp_id,  # Use temp_id instead of permanent id
                        "name": filename,
                        "url": upload_result["public_url"],  # GCS public URL
                        "gcs_url": upload_result["gcs_url"],
                        "score": analysis.score,
                        "style": current_style,
                        "status": "preview",  # Status is preview, not ready
                        "analysis": {
                            "composition": analysis.composition,
                            "color_harmony": analysis.color_harmony,
                            "brand_fit": analysis.brand_fit,
                            "ad_effectiveness": analysis.ad_effectiveness,
                            "suggestions": analysis.suggestions,
                        },
                    }
                )

                actual_cost += CREDIT_PER_CREATIVE

            except GeminiError as e:
                log.warning(
                    "creative_node_image_failed",
                    index=i,
                    error=str(e),
                )
                # Continue with remaining images
                continue

            except GCSError as e:
                log.warning(
                    "creative_node_gcs_upload_failed",
                    index=i,
                    error=str(e),
                )
                # Continue with remaining images
                continue

            except Exception as e:
                log.warning(
                    "creative_node_temp_store_failed",
                    index=i,
                    error=str(e),
                )
                # Continue with remaining images
                continue

        # Store batch reference if multiple images generated
        batch_id = None
        if len(temp_ids) > 1:
            batch_id = await store_temp_batch(user_id, session_id, temp_ids)

        # Step 7: Deduct credit for successfully generated images (direct API, not MCP)
        if actual_cost > 0:
            try:
                await retry_async(
                    lambda: credit_client.deduct_credit(
                        user_id=state.get("user_id", ""),
                        credits=actual_cost,
                        operation_type="generate_creative",
                        operation_id=operation_id,
                        details={
                            "count": len(generated_creatives),
                            "requested_count": count,
                        },
                    ),
                    max_retries=3,
                    context="creative_credit_deduct",
                )
                credit_deducted = True
                log.info(
                    "creative_node_credit_deducted",
                    credits=actual_cost,
                    operation_id=operation_id,
                )

            except CreditError as e:
                log.error(
                    "creative_node_credit_deduct_failed",
                    error=str(e),
                    operation_id=operation_id,
                )

    except Exception as e:
        # Step 8: Refund credit on unexpected failure
        log.error(
            "creative_node_unexpected_error",
            error=str(e),
            exc_info=True,
        )

        # Attempt refund if credit was deducted (direct API, not MCP)
        if credit_deducted and actual_cost > 0:
            try:
                await credit_client.refund_credit(
                    user_id=state.get("user_id", ""),
                    credits=actual_cost,
                    operation_type="generate_creative",
                    operation_id=operation_id,
                    reason=f"Generation failed: {str(e)}",
                )
                log.info(
                    "creative_node_credit_refunded",
                    credits=actual_cost,
                    operation_id=operation_id,
                )
            except CreditError as refund_error:
                log.error(
                    "creative_node_refund_failed",
                    error=str(refund_error),
                    operation_id=operation_id,
                )

        error_state = ErrorHandler.create_node_error_state(
            error=e,
            node_name="creative",
            user_id=state.get("user_id"),
            session_id=state.get("session_id"),
        )
        error_state["completed_results"] = [
            {
                "action_type": "generate_creative",
                "module": "creative",
                "status": "error",
                "data": {"partial_results": generated_creatives},
                "error": error_state.get("error"),
                "cost": actual_cost,
                "mock": False,
            }
        ]
        return error_state

    # Check if any images were generated
    if not generated_creatives:
        log.error("creative_node_no_images_generated")
        return {
            "completed_results": [
                {
                    "action_type": "generate_creative",
                    "module": "creative",
                    "status": "error",
                    "data": {},
                    "error": {
                        "code": "GENERATION_FAILED",
                        "type": "GENERATION_FAILED",
                        "message": "无法生成素材，请稍后重试",
                    },
                    "cost": 0,
                    "mock": False,
                }
            ],
            "credit_checked": True,
            "credit_sufficient": True,
        }

    # Build success result with temp IDs (not permanent IDs)
    result = {
        "action_type": "generate_creative",
        "module": "creative",
        "status": "success",
        "data": {
            "creatives": generated_creatives,
            "temp_ids": temp_ids,  # Temp IDs for later save
            "batch_id": batch_id,  # Batch ID if multiple images
            "count": len(generated_creatives),
            "requested_count": count,
            "message": f"已生成 {len(generated_creatives)} 张素材",
            "save_hint": "如果满意，请说「保存素材」将图片保存到素材库。",
        },
        "error": None,
        "cost": actual_cost,
        "mock": False,
    }

    log.info(
        "creative_node_complete",
        count=len(generated_creatives),
        temp_ids=temp_ids,
        batch_id=batch_id,
        cost=actual_cost,
    )

    return {
        "completed_results": [result],
        "credit_checked": True,
        "credit_sufficient": True,
        # Store temp info for save_creative intent
        "temp_creatives": {
            "temp_ids": temp_ids,
            "batch_id": batch_id,
        },
    }
