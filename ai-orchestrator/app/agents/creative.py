"""Creative Agent - Image and video generation capabilities.

This agent handles:
- Image generation using Gemini native capabilities
- Video generation using Veo 3.1
- Creative analysis and scoring
- Saving creatives to asset library

Requirements: 需求 6 (Ad Creative)
"""

import uuid
from typing import Any

import structlog

from app.agents.base import AgentContext, AgentResult, BaseAgent
from app.services.gemini3_client import (
    AspectRatio,
    FunctionDeclaration,
    Gemini3Client,
    Gemini3Error,
    ImageSize,
    get_gemini3_client,
)
from app.services.gcs_client import get_gcs_client
from app.services.temp_storage import store_temp_creative, store_temp_batch, get_temp_creatives
from app.services.credit_client import get_credit_client, InsufficientCreditsError, CreditError

logger = structlog.get_logger(__name__)

# Credit costs
CREDIT_PER_IMAGE = 0.5
CREDIT_PER_VIDEO = 2.0


class CreativeAgent(BaseAgent):
    """Agent for creative generation (images and videos).

    Supported actions:
    - generate_image: Generate advertising images
    - generate_video: Generate advertising videos
    - analyze_creative: Analyze and score creatives
    - save_creative: Save generated creatives to asset library
    """

    name = "creative_agent"
    description = """生成广告素材的智能助手。可以：
- 生成广告图片（支持多种风格：简约、现代、活力、商务、时尚、科技、自然、奢华）
- 生成广告视频（支持 4/6/8 秒时长）
- 分析和评估素材质量
- 保存素材到素材库

调用示例：
- 生成图片：action="generate_image", params={"prompt": "产品描述", "count": 4, "style": "现代风格"}
- 生成视频：action="generate_video", params={"prompt": "视频描述", "duration": 4}
- 保存素材：action="save_creative", params={"temp_ids": ["id1", "id2"]}"""

    STYLES = {
        "简约风格": "minimalist, clean, white space, modern typography",
        "现代风格": "contemporary, sleek, geometric shapes, bold colors",
        "活力风格": "vibrant, energetic, dynamic composition, bright colors",
        "商务风格": "professional, corporate, trustworthy, blue tones",
        "时尚风格": "trendy, stylish, fashion-forward, editorial quality",
        "科技风格": "futuristic, tech-inspired, digital, neon accents",
        "自然风格": "organic, natural, earthy tones, sustainable feel",
        "奢华风格": "luxury, premium, elegant, gold accents, sophisticated",
    }

    def __init__(self):
        self.gemini_client: Gemini3Client | None = None

    def _get_gemini_client(self) -> Gemini3Client:
        if self.gemini_client is None:
            self.gemini_client = get_gemini3_client()
        return self.gemini_client

    def get_tool_declaration(self) -> FunctionDeclaration:
        """Get function declaration for Gemini function calling."""
        return FunctionDeclaration(
            name=self.name,
            description=self.description,
            parameters={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["generate_image", "generate_video", "analyze_creative", "save_creative"],
                        "description": "要执行的操作",
                    },
                    "params": {
                        "type": "object",
                        "properties": {
                            "prompt": {
                                "type": "string",
                                "description": "产品描述或创意描述",
                            },
                            "count": {
                                "type": "integer",
                                "description": "生成数量（图片 1-10，默认 4）",
                                "default": 4,
                            },
                            "style": {
                                "type": "string",
                                "enum": list(self.STYLES.keys()),
                                "description": "创意风格",
                            },
                            "aspect_ratio": {
                                "type": "string",
                                "enum": ["1:1", "16:9", "9:16", "4:3"],
                                "description": "图片/视频比例",
                                "default": "1:1",
                            },
                            "duration": {
                                "type": "string",
                                "enum": ["4", "6", "8"],
                                "description": "视频时长（秒）",
                                "default": "4",
                            },
                            "temp_ids": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "要保存的素材临时 ID 列表",
                            },
                            "image_size": {
                                "type": "string",
                                "enum": ["1K", "2K", "4K"],
                                "description": "图片尺寸",
                                "default": "2K",
                            },
                        },
                    },
                },
                "required": ["action"],
            },
        )

    async def execute(
        self,
        action: str,
        params: dict[str, Any],
        context: AgentContext,
    ) -> AgentResult:
        """Execute creative action."""
        log = logger.bind(
            user_id=context.user_id,
            session_id=context.session_id,
            agent=self.name,
            action=action,
        )
        log.info("creative_agent_execute")

        try:
            if action == "generate_image":
                return await self._generate_image(params, context)
            elif action == "generate_video":
                return await self._generate_video(params, context)
            elif action == "analyze_creative":
                return await self._analyze_creative(params, context)
            elif action == "save_creative":
                return await self._save_creative(params, context)
            else:
                return AgentResult(
                    success=False,
                    error=f"Unknown action: {action}",
                )
        except Exception as e:
            log.error("creative_agent_error", error=str(e), exc_info=True)
            return AgentResult(
                success=False,
                error=str(e),
            )

    async def _generate_image(
        self,
        params: dict[str, Any],
        context: AgentContext,
    ) -> AgentResult:
        """Generate advertising images."""
        log = logger.bind(user_id=context.user_id, action="generate_image")

        prompt = params.get("prompt", "")
        count = min(params.get("count", 4), 10)
        style = params.get("style")
        aspect_ratio_str = params.get("aspect_ratio", "1:1")
        image_size_str = params.get("image_size", "2K")

        if not prompt:
            return AgentResult(success=False, error="请提供产品描述或创意描述")

        # Map aspect ratio
        aspect_ratio_map = {
            "1:1": AspectRatio.SQUARE,
            "16:9": AspectRatio.LANDSCAPE,
            "9:16": AspectRatio.PORTRAIT,
            "4:3": AspectRatio.STANDARD,
        }
        aspect_ratio = aspect_ratio_map.get(aspect_ratio_str, AspectRatio.SQUARE)

        # Map image size
        image_size_map = {
            "1K": ImageSize.SIZE_1K,
            "2K": ImageSize.SIZE_2K,
            "4K": ImageSize.SIZE_4K,
        }
        image_size = image_size_map.get(image_size_str, ImageSize.SIZE_2K)

        # Estimate cost
        estimated_cost = count * CREDIT_PER_IMAGE
        operation_id = f"creative_img_{uuid.uuid4().hex[:12]}"

        # TODO: Re-enable credit check after backend credit API is fixed
        # Skip credit check for now
        # try:
        #     credit_client = get_credit_client()
        #     await credit_client.check_credit(
        #         user_id=context.user_id,
        #         estimated_credits=estimated_cost,
        #         operation_type="generate_image",
        #     )
        # except InsufficientCreditsError as e:
        #     return AgentResult(
        #         success=False,
        #         error=f"Credit 余额不足。需要 {estimated_cost} credits，当前余额 {e.available}",
        #         data={"required": estimated_cost, "available": e.available},
        #     )
        # except CreditError as e:
        #     return AgentResult(success=False, error=f"Credit 检查失败: {e}")

        # Build enhanced prompt
        enhanced_prompt = self._build_image_prompt(prompt, style)

        log.info("generate_image_start", count=count, style=style)

        gemini = self._get_gemini_client()
        gcs_client = get_gcs_client()

        generated_creatives = []
        temp_ids = []
        actual_cost = 0.0

        # Generate images
        for i in range(count):
            try:
                # Vary style if not specified
                current_style = style or list(self.STYLES.keys())[i % len(self.STYLES)]
                current_prompt = self._build_image_prompt(prompt, current_style)

                # Generate image
                image_bytes = await gemini.generate_image(
                    prompt=current_prompt,
                    aspect_ratio=aspect_ratio,
                    image_size=image_size,
                )

                log.info("image_generated", index=i, size=len(image_bytes))

                # Upload to GCS
                filename = f"{current_style}-{i + 1:02d}.png"
                upload_result = await gcs_client.upload_for_chat_display(
                    image_bytes=image_bytes,
                    filename=filename,
                    user_id=context.user_id,
                    session_id=context.session_id,
                    style=current_style,
                )

                # Store temp reference
                temp_id = await store_temp_creative(
                    user_id=context.user_id,
                    session_id=context.session_id,
                    gcs_url=upload_result["gcs_url"],
                    public_url=upload_result["public_url"],
                    filename=filename,
                    style=current_style,
                    score=85,  # Default score
                    analysis={"object_name": upload_result["object_name"]},
                )
                temp_ids.append(temp_id)

                generated_creatives.append({
                    "temp_id": temp_id,
                    "url": upload_result["public_url"],
                    "style": current_style,
                    "filename": filename,
                })

                actual_cost += CREDIT_PER_IMAGE

            except Gemini3Error as e:
                log.warning("image_generation_failed", index=i, error=str(e))
                continue
            except Exception as e:
                log.warning("image_upload_failed", index=i, error=str(e))
                continue

        # Store batch reference
        batch_id = None
        if len(temp_ids) > 1:
            batch_id = await store_temp_batch(context.user_id, context.session_id, temp_ids)

        # TODO: Re-enable credit deduct after backend credit API is fixed
        # Skip credit deduct for now
        # if actual_cost > 0:
        #     try:
        #         await credit_client.deduct_credit(
        #             user_id=context.user_id,
        #             credits=actual_cost,
        #             operation_type="generate_image",
        #             operation_id=operation_id,
        #             details={"count": len(generated_creatives)},
        #         )
        #     except CreditError as e:
        #         log.error("credit_deduct_failed", error=str(e))

        if not generated_creatives:
            return AgentResult(
                success=False,
                error="无法生成素材，请稍后重试",
            )

        return AgentResult(
            success=True,
            data={
                "creatives": generated_creatives,
                "temp_ids": temp_ids,
                "batch_id": batch_id,
                "count": len(generated_creatives),
            },
            credit_consumed=actual_cost,
            message=f"已生成 {len(generated_creatives)} 张素材。如果满意，请说「保存素材」将图片保存到素材库。",
        )

    async def _generate_video(
        self,
        params: dict[str, Any],
        context: AgentContext,
    ) -> AgentResult:
        """Generate advertising video using Veo 3.1."""
        log = logger.bind(user_id=context.user_id, action="generate_video")

        prompt = params.get("prompt", "")
        duration_str = params.get("duration", "4")
        # Handle both string and int duration
        duration = int(duration_str) if isinstance(duration_str, str) else duration_str
        aspect_ratio_str = params.get("aspect_ratio", "16:9")

        if not prompt:
            return AgentResult(success=False, error="请提供视频描述")

        # Validate duration
        if duration not in [4, 6, 8]:
            duration = 4

        # Map aspect ratio
        aspect_ratio = AspectRatio.LANDSCAPE if aspect_ratio_str == "16:9" else AspectRatio.PORTRAIT

        # Estimate cost
        estimated_cost = CREDIT_PER_VIDEO
        operation_id = f"creative_vid_{uuid.uuid4().hex[:12]}"

        # TODO: Re-enable credit check after backend credit API is fixed
        # Skip credit check for now
        # try:
        #     credit_client = get_credit_client()
        #     await credit_client.check_credit(
        #         user_id=context.user_id,
        #         estimated_credits=estimated_cost,
        #         operation_type="generate_video",
        #     )
        # except InsufficientCreditsError as e:
        #     return AgentResult(
        #         success=False,
        #         error=f"Credit 余额不足。需要 {estimated_cost} credits，当前余额 {e.available}",
        #     )

        log.info("generate_video_start", duration=duration)

        gemini = self._get_gemini_client()

        try:
            # Start video generation
            result = await gemini.generate_video(
                prompt=prompt,
                duration=duration,
                aspect_ratio=aspect_ratio,
            )

            operation_id_veo = result.get("operation_id")

            if not operation_id_veo:
                return AgentResult(success=False, error="视频生成启动失败")

            # Poll for completion (with timeout)
            video_result = await gemini.poll_video_operation(
                operation_id=operation_id_veo,
                poll_interval=10.0,
                max_wait=300.0,
            )

            # TODO: Re-enable credit deduct after backend credit API is fixed
            # Skip credit deduct for now
            # await credit_client.deduct_credit(
            #     user_id=context.user_id,
            #     credits=CREDIT_PER_VIDEO,
            #     operation_type="generate_video",
            #     operation_id=operation_id,
            # )

            return AgentResult(
                success=True,
                data={
                    "video_url": video_result.get("video_url"),
                    "duration": video_result.get("duration"),
                    "status": "completed",
                },
                credit_consumed=CREDIT_PER_VIDEO,
                message=f"视频生成完成！时长 {duration} 秒。",
            )

        except Gemini3Error as e:
            log.error("video_generation_failed", error=str(e))
            return AgentResult(success=False, error=f"视频生成失败: {e}")

    async def _analyze_creative(
        self,
        params: dict[str, Any],
        context: AgentContext,
    ) -> AgentResult:
        """Analyze and score a creative."""
        # TODO: Implement creative analysis using Gemini vision
        return AgentResult(
            success=True,
            data={"score": 85, "analysis": "Creative analysis not yet implemented"},
            message="素材分析功能开发中",
        )

    async def _save_creative(
        self,
        params: dict[str, Any],
        context: AgentContext,
    ) -> AgentResult:
        """Save generated creatives to asset library via MCP."""
        log = logger.bind(user_id=context.user_id, action="save_creative")

        temp_ids = params.get("temp_ids", [])

        if not temp_ids:
            # Try to get from recent session
            creatives = await get_temp_creatives(context.user_id, context.session_id)
            if not creatives:
                return AgentResult(
                    success=False,
                    error="没有找到待保存的素材。请先生成素材。",
                )
            temp_ids = list(creatives.keys())

        log.info("save_creative_start", count=len(temp_ids))

        # Get temp creatives metadata
        creatives = await get_temp_creatives(context.user_id, context.session_id)

        # Get MCP client
        from app.agents.mcp_integration import get_agent_mcp_client
        mcp_client = get_agent_mcp_client()

        saved_ids = []
        saved_creative_ids = []
        errors = []

        for temp_id in temp_ids:
            if temp_id not in creatives:
                errors.append(f"素材 {temp_id} 不存在或已过期")
                continue

            creative_data = creatives[temp_id]

            try:
                # Call MCP to save creative to backend
                result = await mcp_client.create_creative(
                    user_id=context.user_id,
                    url=creative_data.get("public_url", ""),
                    filename=creative_data.get("filename", ""),
                    style=creative_data.get("style"),
                    score=creative_data.get("score"),
                    analysis=creative_data.get("analysis"),
                )
                saved_ids.append(temp_id)
                saved_creative_ids.append(result.get("id"))
                log.info("creative_saved", temp_id=temp_id, creative_id=result.get("id"))

            except Exception as e:
                errors.append(f"保存 {temp_id} 失败: {e}")
                log.error("save_creative_failed", temp_id=temp_id, error=str(e))

        if not saved_ids:
            return AgentResult(
                success=False,
                error=f"保存失败: {'; '.join(errors)}",
            )

        return AgentResult(
            success=True,
            data={
                "saved_ids": saved_ids,
                "creative_ids": saved_creative_ids,
                "failed": errors,
            },
            message=f"已保存 {len(saved_ids)} 个素材到素材库。",
        )

    def _build_image_prompt(self, base_prompt: str, style: str | None) -> str:
        """Build enhanced prompt for image generation."""
        prompt = f"Professional advertising creative image for {base_prompt}"

        if style and style in self.STYLES:
            prompt += f", {self.STYLES[style]} style"

        prompt += ", high quality, professional photography, studio lighting"
        prompt += ", suitable for digital advertising, eye-catching"

        return prompt


# Singleton instance
_creative_agent: CreativeAgent | None = None


def get_creative_agent() -> CreativeAgent:
    """Get or create CreativeAgent singleton."""
    global _creative_agent
    if _creative_agent is None:
        _creative_agent = CreativeAgent()
    return _creative_agent


# Tool declaration for registration
creative_agent_tool = get_creative_agent().get_tool_declaration()
