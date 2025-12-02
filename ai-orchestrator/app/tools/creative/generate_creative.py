"""Generate Creative Tool - AI-powered ad creative generation.

This tool generates advertising creative images using Gemini Imagen 3,
uploads them to GCS for preview, and stores temporary references.

Requirements: Architecture v2.0 - Unified Tool Layer
"""

import time
import uuid
from typing import Any, Literal

import structlog
from pydantic import BaseModel, Field

from app.tools.base import (
    BaseTool,
    ToolCategory,
    ToolContext,
    ToolDefinition,
    ToolResult,
    ToolRiskLevel,
)

logger = structlog.get_logger(__name__)

# Credit cost per image
CREDIT_PER_IMAGE = 0.5

# Supported styles
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


class GenerateCreativeInput(BaseModel):
    """Input parameters for generate_creative tool."""

    product_description: str = Field(description="Product description for creative")
    product_url: str | None = Field(
        default=None, description="Product URL for reference"
    )
    style: str | None = Field(
        default=None,
        description="Creative style: 简约风格, 现代风格, 活力风格, 商务风格, 时尚风格, 科技风格, 自然风格, 奢华风格",
    )
    count: int = Field(default=4, ge=1, le=20, description="Number of images to generate")
    aspect_ratio: Literal["1:1", "16:9", "9:16", "4:3"] = Field(
        default="1:1", description="Image aspect ratio"
    )
    target_audience: str | None = Field(
        default=None, description="Target audience description"
    )
    platform: Literal["meta", "tiktok", "google", "all"] = Field(
        default="all", description="Target ad platform"
    )


class GeneratedCreative(BaseModel):
    """Single generated creative."""

    temp_id: str
    url: str
    style: str
    score: int = 80
    analysis: dict[str, Any] = Field(default_factory=dict)


class GenerateCreativeOutput(BaseModel):
    """Output from generate_creative tool."""

    creatives: list[GeneratedCreative]
    batch_id: str | None = None
    total_generated: int
    save_hint: str = "如果满意，请说「保存素材」将图片保存到素材库"


class GenerateCreativeTool(BaseTool[GenerateCreativeInput, GenerateCreativeOutput]):
    """Tool for generating ad creative images.

    Uses Gemini Imagen 3 for image generation, uploads to GCS,
    and returns preview URLs with temporary IDs for later saving.
    """

    definition = ToolDefinition(
        name="generate_creative",
        description=(
            "使用AI生成广告素材图片。支持多种风格（简约、现代、活力、商务等），"
            "可指定尺寸比例和目标平台。生成后可预览，满意后再保存到素材库。"
        ),
        category=ToolCategory.CREATIVE,
        risk_level=ToolRiskLevel.LOW,
        credit_cost=CREDIT_PER_IMAGE,  # Base cost, actual varies by count
        requires_confirmation=False,
        parameters=GenerateCreativeInput.model_json_schema(),
        returns=GenerateCreativeOutput.model_json_schema(),
    )

    def estimate_cost(self, params: GenerateCreativeInput) -> float:
        """Calculate credit cost based on image count."""
        return CREDIT_PER_IMAGE * params.count

    async def execute(
        self, params: GenerateCreativeInput, context: ToolContext
    ) -> ToolResult:
        """Execute creative generation.

        Args:
            params: Generation parameters
            context: Execution context

        Returns:
            ToolResult with generated creatives or error
        """
        log = logger.bind(
            user_id=context.user_id,
            session_id=context.session_id,
            tool="generate_creative",
        )
        log.info(
            "generate_creative_start",
            count=params.count,
            style=params.style,
        )

        start_time = time.time()
        operation_id = f"creative_{uuid.uuid4().hex[:12]}"
        estimated_cost = self.estimate_cost(params)

        try:
            # Import services here to avoid circular imports
            from app.services.credit_client import get_credit_client, InsufficientCreditsError
            from app.services.gemini_client import GeminiClient, GeminiError
            from app.services.gcs_client import get_gcs_client
            from app.services.temp_storage import store_temp_creative, store_temp_batch

            # Check credits
            credit_client = get_credit_client()
            try:
                await credit_client.check_credit(
                    user_id=context.user_id,
                    estimated_credits=estimated_cost,
                    operation_type="generate_creative",
                )
            except InsufficientCreditsError as e:
                return ToolResult.error_result(
                    error=f"Credit 余额不足。需要 {estimated_cost} credits，当前余额 {e.available}",
                    data={"required": estimated_cost, "available": e.available},
                )

            # Initialize clients
            from app.nodes.creative_node import ImagenClient, build_image_prompt, analyze_creative

            imagen_client = ImagenClient()
            gemini_client = GeminiClient()
            gcs_client = get_gcs_client()

            generated_creatives: list[GeneratedCreative] = []
            temp_ids: list[str] = []
            actual_cost = 0.0

            # Generate images
            for i in range(params.count):
                try:
                    # Vary style for each image if not specified
                    current_style = params.style or CREATIVE_STYLES[i % len(CREATIVE_STYLES)]

                    # Build prompt
                    prompt = build_image_prompt(
                        product_url=params.product_url,
                        product_description=params.product_description,
                        style=current_style,
                        target_audience=params.target_audience,
                    )

                    # Generate image
                    image_bytes = await imagen_client.generate_image(
                        prompt=prompt,
                        aspect_ratio=params.aspect_ratio,
                    )

                    log.info("creative_image_generated", index=i, size=len(image_bytes))

                    # Analyze image
                    analysis = await analyze_creative(image_bytes, gemini_client)

                    # Upload to GCS
                    filename = f"{current_style}-{i + 1:02d}.png"
                    upload_result = await gcs_client.upload_for_chat_display(
                        image_bytes=image_bytes,
                        filename=filename,
                        user_id=context.user_id,
                        session_id=context.session_id,
                        style=current_style,
                        score=analysis.score,
                    )

                    # Store temp reference
                    temp_id = await store_temp_creative(
                        user_id=context.user_id,
                        session_id=context.session_id,
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
                        },
                    )
                    temp_ids.append(temp_id)

                    generated_creatives.append(
                        GeneratedCreative(
                            temp_id=temp_id,
                            url=upload_result["public_url"],
                            style=current_style,
                            score=analysis.score,
                            analysis={
                                "composition": analysis.composition,
                                "color_harmony": analysis.color_harmony,
                                "ad_effectiveness": analysis.ad_effectiveness,
                            },
                        )
                    )

                    actual_cost += CREDIT_PER_IMAGE

                except GeminiError as e:
                    log.warning("creative_image_failed", index=i, error=str(e))
                    continue
                except Exception as e:
                    log.warning("creative_image_error", index=i, error=str(e))
                    continue

            # Store batch reference
            batch_id = None
            if len(temp_ids) > 1:
                batch_id = await store_temp_batch(
                    context.user_id, context.session_id, temp_ids
                )

            # Deduct credits
            if actual_cost > 0:
                await credit_client.deduct_credit(
                    user_id=context.user_id,
                    credits=actual_cost,
                    operation_type="generate_creative",
                    operation_id=operation_id,
                    details={"count": len(generated_creatives)},
                )

            execution_time = time.time() - start_time

            if not generated_creatives:
                return ToolResult.error_result(
                    error="无法生成素材，请稍后重试",
                )

            output = GenerateCreativeOutput(
                creatives=generated_creatives,
                batch_id=batch_id,
                total_generated=len(generated_creatives),
            )

            log.info(
                "generate_creative_success",
                count=len(generated_creatives),
                cost=actual_cost,
                execution_time=execution_time,
            )

            return ToolResult.success_result(
                data=output.model_dump(),
                credit_consumed=actual_cost,
                execution_time=execution_time,
                temp_ids=temp_ids,
                batch_id=batch_id,
            )

        except Exception as e:
            log.error("generate_creative_error", error=str(e), exc_info=True)
            return ToolResult.error_result(
                error=f"生成素材失败: {str(e)}",
            )

    def validate_params(self, params: dict[str, Any]) -> GenerateCreativeInput:
        """Validate input parameters."""
        return GenerateCreativeInput(**params)
