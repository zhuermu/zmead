"""
Ad Creative capability - Main entry point for the module.

This module provides the main entry point for Ad Creative functionality,
including creative generation, analysis, scoring, and management.

Requirements: 1.1, 2.1, 3.1, 4.1, 5.1, 6.1, 7.1, 8.1, 9.1, 10.1
"""

import structlog
from redis.asyncio import Redis

from app.core.errors import ErrorHandler
from app.services.gemini_client import GeminiClient, GeminiError
from app.services.mcp_client import MCPClient, MCPError
from .models import (
    GenerateCreativeRequest,
    GenerateCreativeResponse,
    AnalyzeCreativeResponse,
    ScoreCreativeResponse,
    GetCreativesRequest,
    GetCreativesResponse,
    Creative,
)

logger = structlog.get_logger(__name__)


class AdCreative:
    """Ad Creative 功能模块主入口

    Provides comprehensive ad creative capabilities including:
    - Product information extraction (Shopify, Amazon)
    - AI-powered creative generation (Gemini Imagen 3)
    - Creative scoring with multi-dimensional evaluation
    - Competitor creative analysis
    - Creative library management
    - Platform-specific aspect ratio handling
    - Credit balance control

    Requirements: 1.1, 2.1, 3.1, 4.1, 5.1, 6.1, 7.1, 8.1, 9.1, 10.1
    """

    # Supported actions for routing
    SUPPORTED_ACTIONS = [
        "generate_creative",
        "generate_from_reference",  # Image-to-Image generation
        "analyze_creative",
        "score_creative",
        "generate_variants",
        "analyze_competitor",
        "get_creatives",
        "delete_creative",
        "download_creative",
        "batch_download",
        "upload_reference",
        "generate_video",  # Video generation
        "check_video_status",  # Check video generation status
    ]

    def __init__(
        self,
        mcp_client: MCPClient | None = None,
        gemini_client: GeminiClient | None = None,
        redis_client: Redis | None = None,
    ):
        """初始化 Ad Creative 模块

        Args:
            mcp_client: MCP client for Web Platform communication
            gemini_client: Gemini client for AI generation and analysis
            redis_client: Redis client for caching
        """
        # Initialize dependencies
        self.mcp_client = mcp_client or MCPClient()
        self.gemini_client = gemini_client or GeminiClient()
        self.redis_client = redis_client

        logger.info(
            "ad_creative_initialized",
            has_mcp=self.mcp_client is not None,
            has_gemini=self.gemini_client is not None,
            has_redis=self.redis_client is not None,
        )

    async def execute(self, action: str, parameters: dict, context: dict) -> dict:
        """
        执行素材生成操作

        Implements action routing with comprehensive error handling and logging.
        All errors are caught and converted to structured error responses.

        Args:
            action: 操作名称 (generate_creative, analyze_creative, etc.)
            parameters: 操作参数
            context: 上下文信息（user_id, session_id等）

        Returns:
            操作结果，格式：
            - 成功: {"status": "success", "data": {...}, "message": "..."}
            - 失败: {"status": "error", "error": {...}}

        Requirements: Module API
        """
        user_id = context.get("user_id")
        session_id = context.get("session_id")

        log = logger.bind(
            action=action,
            user_id=user_id,
            session_id=session_id,
        )

        log.info("ad_creative_execute_start", parameters=parameters)

        try:
            # Route to appropriate handler
            if action == "generate_creative":
                result = await self._generate_creative(parameters, context)
            elif action == "generate_from_reference":
                result = await self._generate_from_reference(parameters, context)
            elif action == "analyze_creative":
                result = await self._analyze_creative(parameters, context)
            elif action == "score_creative":
                result = await self._score_creative(parameters, context)
            elif action == "generate_variants":
                result = await self._generate_variants(parameters, context)
            elif action == "analyze_competitor":
                result = await self._analyze_competitor(parameters, context)
            elif action == "get_creatives":
                result = await self._get_creatives(parameters, context)
            elif action == "delete_creative":
                result = await self._delete_creative(parameters, context)
            elif action == "download_creative":
                result = await self._download_creative(parameters, context)
            elif action == "batch_download":
                result = await self._batch_download(parameters, context)
            elif action == "upload_reference":
                result = await self._upload_reference(parameters, context)
            elif action == "generate_video":
                result = await self._generate_video(parameters, context)
            elif action == "check_video_status":
                result = await self._check_video_status(parameters, context)
            else:
                log.warning("unknown_action", action=action)
                return {
                    "status": "error",
                    "error": {
                        "code": "1001",
                        "type": "INVALID_ACTION",
                        "message": f"Unknown action: {action}",
                        "details": {
                            "action": action,
                            "supported_actions": self.SUPPORTED_ACTIONS,
                        },
                    },
                }

            log.info("ad_creative_execute_success", action=action)
            return result

        except (MCPError, GeminiError) as e:
            # Handle known service errors
            log.error(
                "ad_creative_service_error",
                error=str(e),
                error_type=type(e).__name__,
            )
            error_state = ErrorHandler.handle_error(
                error=e,
                context=f"ad_creative.{action}",
                user_id=user_id,
                session_id=session_id,
            )
            return {
                "status": "error",
                **error_state,
            }

        except Exception as e:
            # Handle unexpected errors
            log.error(
                "ad_creative_unexpected_error",
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )
            error_state = ErrorHandler.handle_error(
                error=e,
                context=f"ad_creative.{action}",
                user_id=user_id,
                session_id=session_id,
            )
            return {
                "status": "error",
                **error_state,
            }


    async def _generate_creative(self, parameters: dict, context: dict) -> dict:
        """生成素材

        Generates creative assets using AI based on product information.

        Args:
            parameters: {
                "product_url": str (optional),
                "product_info": dict (optional),
                "count": 3 | 10,
                "style": str,
                "platform": "tiktok" | "instagram" | "facebook" (optional),
                "aspect_ratio": str (optional, custom ratio)
            }
            context: {"user_id": str, "session_id": str}

        Returns:
            GenerateCreativeResponse

        Requirements: 1.1, 4.1, 4.2, 5.1, 9.1
        """
        logger.info("generate_creative_stub", parameters=parameters)

        # TODO: Implement in task 2 (product extraction) and task 4 (image generation)
        return {
            "status": "success",
            "creative_ids": [],
            "creatives": [],
            "message": "Creative generation not yet implemented (tasks 2, 4)",
        }

    async def _analyze_creative(self, parameters: dict, context: dict) -> dict:
        """分析素材

        Analyzes creative assets using AI vision.

        Args:
            parameters: {
                "creative_id": str (optional),
                "image_url": str (optional)
            }
            context: {"user_id": str, "session_id": str}

        Returns:
            AnalyzeCreativeResponse

        Requirements: 7.1
        """
        logger.info("analyze_creative_stub", parameters=parameters)

        # TODO: Implement in task 6 (scoring engine)
        return {
            "status": "success",
            "insights": None,
            "recommendations": [],
            "message": "Creative analysis not yet implemented (task 6)",
        }

    async def _score_creative(self, parameters: dict, context: dict) -> dict:
        """评分素材

        Scores creative assets using multi-dimensional AI evaluation.

        Args:
            parameters: {
                "creative_id": str
            }
            context: {"user_id": str, "session_id": str}

        Returns:
            ScoreCreativeResponse

        Requirements: 7.1, 7.2, 7.3
        """
        logger.info("score_creative_stub", parameters=parameters)

        # TODO: Implement in task 6 (scoring engine)
        return {
            "status": "success",
            "score": None,
            "message": "Creative scoring not yet implemented (task 6)",
        }

    async def _generate_variants(self, parameters: dict, context: dict) -> dict:
        """生成变体

        Generates variants based on an existing creative.

        Args:
            parameters: {
                "creative_id": str,
                "count": int,
                "variation_type": str (optional, default "style")
            }
            context: {"user_id": str, "session_id": str}

        Returns:
            GenerateCreativeResponse

        Requirements: 6.4
        """
        user_id = context.get("user_id")
        creative_id = parameters.get("creative_id")
        count = parameters.get("count", 3)
        variation_type = parameters.get("variation_type", "style")

        log = logger.bind(
            user_id=user_id,
            creative_id=creative_id,
            count=count,
            variation_type=variation_type,
        )
        log.info("generate_variants_start")

        if not creative_id:
            return {
                "status": "error",
                "error": {
                    "code": "6006",
                    "type": "INVALID_PARAMS",
                    "message": "creative_id is required",
                },
            }

        try:
            # Import here to avoid circular imports
            from .generators.variant_generator import (
                VariantGenerator,
                VariantGenerationError,
            )
            from .managers.upload_manager import UploadManager

            generator = VariantGenerator(
                gemini_client=self.gemini_client,
                mcp_client=self.mcp_client,
            )

            try:
                # Generate variants
                variants = await generator.generate_variants(
                    user_id=user_id,
                    creative_id=creative_id,
                    count=count,
                    variation_type=variation_type,
                )

                # Upload generated variants
                upload_manager = UploadManager(mcp_client=self.mcp_client)
                uploaded_creatives = []

                for variant in variants:
                    try:
                        result = await upload_manager.upload_creative(
                            user_id=user_id,
                            image=variant,
                            metadata={
                                "type": "variant",
                                "original_creative_id": creative_id,
                                "variation_type": variation_type,
                            },
                        )
                        uploaded_creatives.append({
                            "creative_id": result.creative_id,
                            "url": result.url,
                            "created_at": result.created_at,
                        })
                    except Exception as e:
                        log.warning("variant_upload_failed", error=str(e))

                await upload_manager.close()

                log.info(
                    "generate_variants_complete",
                    generated=len(variants),
                    uploaded=len(uploaded_creatives),
                )

                return {
                    "status": "success",
                    "creative_ids": [c["creative_id"] for c in uploaded_creatives],
                    "creatives": uploaded_creatives,
                    "message": f"成功生成 {len(uploaded_creatives)} 个变体",
                }

            except VariantGenerationError as e:
                log.error("generate_variants_failed", error=str(e), code=e.code)
                return {
                    "status": "error",
                    "error": {
                        "code": e.code or "4003",
                        "type": "VARIANT_GENERATION_FAILED",
                        "message": f"变体生成失败: {e.message}",
                    },
                }

        except Exception as e:
            log.error("generate_variants_error", error=str(e))
            raise

    async def _analyze_competitor(self, parameters: dict, context: dict) -> dict:
        """分析竞品素材

        Analyzes competitor ad creatives from TikTok.

        Args:
            parameters: {
                "ad_url": str,
                "save": bool (optional, default True)
            }
            context: {"user_id": str, "session_id": str}

        Returns:
            CompetitorAnalysis result

        Requirements: 3.1, 3.2, 3.3, 3.5
        """
        user_id = context.get("user_id")
        ad_url = parameters.get("ad_url")
        save_result = parameters.get("save", True)

        log = logger.bind(user_id=user_id, ad_url=ad_url)
        log.info("analyze_competitor_start")

        if not ad_url:
            return {
                "status": "error",
                "error": {
                    "code": "6006",
                    "type": "INVALID_PARAMS",
                    "message": "ad_url is required",
                },
            }

        try:
            # Import here to avoid circular imports
            from .analyzers.competitor_analyzer import (
                CompetitorAnalyzer,
                CompetitorAnalyzerError,
            )

            analyzer = CompetitorAnalyzer(
                gemini_client=self.gemini_client,
                mcp_client=self.mcp_client,
            )

            try:
                if save_result:
                    # Analyze and save
                    analysis = await analyzer.analyze_and_save(user_id, ad_url)
                else:
                    # Just analyze without saving
                    analysis = await analyzer.analyze(ad_url)

                log.info(
                    "analyze_competitor_complete",
                    selling_points_count=len(analysis.selling_points),
                    saved=analysis.saved_at is not None,
                )

                return {
                    "status": "success",
                    "analysis": {
                        "composition": analysis.composition,
                        "color_scheme": analysis.color_scheme,
                        "selling_points": analysis.selling_points,
                        "copy_structure": analysis.copy_structure,
                        "recommendations": analysis.recommendations,
                        "saved_at": analysis.saved_at,
                    },
                    "message": "竞品素材分析完成",
                }

            except CompetitorAnalyzerError as e:
                log.error("analyze_competitor_failed", error=str(e), code=e.code)
                return {
                    "status": "error",
                    "error": {
                        "code": e.code or "6007",
                        "type": "COMPETITOR_ANALYSIS_FAILED",
                        "message": f"竞品分析失败: {e.message}",
                    },
                }

            finally:
                await analyzer.close()

        except Exception as e:
            log.error("analyze_competitor_error", error=str(e))
            raise

    async def _get_creatives(self, parameters: dict, context: dict) -> dict:
        """获取素材列表

        Retrieves user's creative library with filtering and sorting.

        Args:
            parameters: {
                "filters": dict,
                "sort_by": str,
                "sort_order": "asc" | "desc",
                "limit": int,
                "offset": int
            }
            context: {"user_id": str, "session_id": str}

        Returns:
            GetCreativesResponse

        Requirements: 8.1, 8.2, 7.5, 10.2
        """
        user_id = context.get("user_id")
        log = logger.bind(user_id=user_id)
        log.info("get_creatives_start", parameters=parameters)

        try:
            # Parse request parameters
            filters = parameters.get("filters", {})
            sort_by = parameters.get("sort_by", "score")
            sort_order = parameters.get("sort_order", "desc")
            limit = parameters.get("limit", 20)
            offset = parameters.get("offset", 0)

            # Call MCP to get creatives
            result = await self.mcp_client.call_tool(
                "get_creatives",
                {
                    "user_id": user_id,
                    "filters": filters,
                    "sort_by": sort_by,
                    "sort_order": sort_order,
                    "limit": limit,
                    "offset": offset,
                },
            )

            creatives = [Creative(**c) for c in result.get("creatives", [])]
            total = result.get("total", 0)

            # Check capacity warning (> 100 creatives)
            capacity_warning = total > 100

            log.info(
                "get_creatives_complete",
                count=len(creatives),
                total=total,
                capacity_warning=capacity_warning,
            )

            return {
                "status": "success",
                "creatives": [c.model_dump() for c in creatives],
                "total": total,
                "capacity_warning": capacity_warning,
                "message": "素材列表获取成功" + ("，建议清理旧素材" if capacity_warning else ""),
            }

        except MCPError as e:
            log.error("get_creatives_failed", error=str(e))
            raise

    async def _delete_creative(self, parameters: dict, context: dict) -> dict:
        """删除素材

        Deletes a creative from the library.

        Args:
            parameters: {
                "creative_id": str
            }
            context: {"user_id": str, "session_id": str}

        Returns:
            Success/error response

        Requirements: 6.3, 8.4
        """
        user_id = context.get("user_id")
        creative_id = parameters.get("creative_id")

        log = logger.bind(user_id=user_id, creative_id=creative_id)
        log.info("delete_creative_start")

        try:
            # Call MCP to delete creative
            await self.mcp_client.call_tool(
                "delete_creative",
                {
                    "creative_id": creative_id,
                    "user_id": user_id,
                },
            )

            log.info("delete_creative_complete")

            return {
                "status": "success",
                "message": "素材删除成功",
            }

        except MCPError as e:
            log.error("delete_creative_failed", error=str(e))
            raise

    async def _download_creative(self, parameters: dict, context: dict) -> dict:
        """下载素材

        Gets download URL for a single creative.

        Args:
            parameters: {
                "creative_id": str
            }
            context: {"user_id": str, "session_id": str}

        Returns:
            Download URL

        Requirements: 6.2
        """
        user_id = context.get("user_id")
        creative_id = parameters.get("creative_id")

        log = logger.bind(user_id=user_id, creative_id=creative_id)
        log.info("download_creative_start")

        try:
            # Call MCP to get download URL
            result = await self.mcp_client.call_tool(
                "get_creative_download_url",
                {
                    "creative_id": creative_id,
                    "user_id": user_id,
                },
            )

            log.info("download_creative_complete")

            return {
                "status": "success",
                "download_url": result.get("download_url"),
                "message": "下载链接获取成功",
            }

        except MCPError as e:
            log.error("download_creative_failed", error=str(e))
            raise

    async def _batch_download(self, parameters: dict, context: dict) -> dict:
        """批量下载素材

        Gets download URL for multiple creatives (zip archive).

        Args:
            parameters: {
                "creative_ids": list[str]
            }
            context: {"user_id": str, "session_id": str}

        Returns:
            Download URL for zip archive

        Requirements: 8.3
        """
        user_id = context.get("user_id")
        creative_ids = parameters.get("creative_ids", [])

        log = logger.bind(user_id=user_id, creative_count=len(creative_ids))
        log.info("batch_download_start")

        try:
            # Call MCP to get batch download URL
            result = await self.mcp_client.call_tool(
                "get_batch_download_url",
                {
                    "creative_ids": creative_ids,
                    "user_id": user_id,
                },
            )

            log.info("batch_download_complete")

            return {
                "status": "success",
                "download_url": result.get("download_url"),
                "message": f"批量下载链接获取成功（{len(creative_ids)} 个素材）",
            }

        except MCPError as e:
            log.error("batch_download_failed", error=str(e))
            raise

    async def _upload_reference(self, parameters: dict, context: dict) -> dict:
        """上传参考图片

        Uploads reference images for creative generation.
        Accepts already-uploaded file URLs from the frontend.

        Args:
            parameters: {
                "files": list[dict] - List of uploaded files with urls
                    Each file: {
                        "name": str,
                        "url": str (CDN URL),
                        "s3_url": str (S3 URL),
                        "type": str (file type category),
                        "mime_type": str,
                        "size": int
                    }
                "purpose": str - Purpose of the references (default: "creative_generation")
            }
            context: {"user_id": str, "session_id": str}

        Returns:
            Upload result with reference IDs

        Requirements: 2.1, 2.2, 2.3, 2.5
        """
        user_id = context.get("user_id")
        files = parameters.get("files", [])
        purpose = parameters.get("purpose", "creative_generation")

        log = logger.bind(
            user_id=user_id,
            file_count=len(files),
            purpose=purpose,
        )
        log.info("upload_reference_start")

        if not files:
            return {
                "status": "error",
                "error": {
                    "code": "6006",
                    "type": "INVALID_PARAMS",
                    "message": "No files provided",
                },
            }

        # Validate file types
        allowed_types = ["image", "video"]
        invalid_files = [f for f in files if f.get("type") not in allowed_types]
        if invalid_files:
            return {
                "status": "error",
                "error": {
                    "code": "6006",
                    "type": "INVALID_FILE_TYPE",
                    "message": f"Invalid file types: {[f.get('name') for f in invalid_files]}. Only images and videos are allowed as references.",
                },
            }

        try:
            # Store references via MCP
            stored_references = []
            for file_info in files:
                try:
                    result = await self.mcp_client.call_tool(
                        "store_reference",
                        {
                            "user_id": user_id,
                            "file_url": file_info.get("url") or file_info.get("s3_url"),
                            "file_name": file_info.get("name"),
                            "file_type": file_info.get("type"),
                            "mime_type": file_info.get("mime_type"),
                            "file_size": file_info.get("size"),
                            "purpose": purpose,
                        },
                    )
                    stored_references.append({
                        "reference_id": result.get("reference_id"),
                        "name": file_info.get("name"),
                        "url": file_info.get("url"),
                        "type": file_info.get("type"),
                    })
                except MCPError as e:
                    log.warning(
                        "store_reference_failed",
                        file_name=file_info.get("name"),
                        error=str(e),
                    )
                    # Continue with other files
                    continue

            if not stored_references:
                return {
                    "status": "error",
                    "error": {
                        "code": "5003",
                        "type": "STORAGE_ERROR",
                        "message": "Failed to store any reference files",
                    },
                }

            log.info(
                "upload_reference_complete",
                stored_count=len(stored_references),
            )

            return {
                "status": "success",
                "references": stored_references,
                "reference_ids": [r["reference_id"] for r in stored_references],
                "message": f"成功保存 {len(stored_references)} 个参考文件",
            }

        except Exception as e:
            log.error("upload_reference_error", error=str(e))
            raise

    async def _generate_from_reference(self, parameters: dict, context: dict) -> dict:
        """基于参考图生成新素材 (Image-to-Image)

        Generates new creatives based on uploaded reference images.
        Uses Gemini's image editing/variation capabilities.

        Args:
            parameters: {
                "reference_urls": list[str] - URLs of reference images
                "prompt": str - Description of desired output
                "style": str - Style to apply
                "count": int - Number of variations to generate
                "strength": float - How much to vary from reference (0.0-1.0)
            }
            context: {"user_id": str, "session_id": str}

        Returns:
            Generated creative results

        Requirements: 4.2, 6.4
        """
        user_id = context.get("user_id")
        reference_urls = parameters.get("reference_urls", [])
        prompt = parameters.get("prompt", "")
        style = parameters.get("style", "modern")
        count = parameters.get("count", 3)
        strength = parameters.get("strength", 0.7)

        log = logger.bind(
            user_id=user_id,
            reference_count=len(reference_urls),
            style=style,
            count=count,
        )
        log.info("generate_from_reference_start")

        if not reference_urls:
            return {
                "status": "error",
                "error": {
                    "code": "6006",
                    "type": "INVALID_PARAMS",
                    "message": "No reference images provided. Please upload reference images first.",
                },
            }

        try:
            # Import image generator
            from .generators.image_generator import ImageGenerator, ImageGenerationError

            # Check credits first
            estimated_cost = count * 0.5  # 0.5 credits per image
            try:
                await self.mcp_client.call_tool(
                    "check_credit",
                    {
                        "user_id": user_id,
                        "required_credits": estimated_cost,
                        "operation_type": "generate_from_reference",
                    },
                )
            except MCPError as e:
                if "insufficient" in str(e).lower():
                    return {
                        "status": "error",
                        "error": {
                            "code": "6011",
                            "type": "INSUFFICIENT_CREDITS",
                            "message": f"Credit 不足，需要 {estimated_cost} credits",
                        },
                    }
                raise

            # Build enhanced prompt with reference context
            enhanced_prompt = f"""Based on the reference image(s), create a new advertising creative.
Style: {style}
Instructions: {prompt if prompt else 'Generate a similar but unique variation'}
Maintain the product focus while applying the requested style."""

            # Generate using Gemini (with reference image context)
            generator = ImageGenerator(gemini_client=self.gemini_client)

            # For now, we use text-to-image with detailed prompt
            # TODO: When Imagen 3 supports image-to-image, use that API
            from .models import ProductInfo

            # Create a synthetic product info from the prompt
            product_info = ProductInfo(
                title=prompt or "Product variation",
                price=0,
                currency="USD",
                images=reference_urls,
                description=prompt or "Generate variation based on reference",
                selling_points=[],
                source="manual",
            )

            try:
                images = await generator.generate(
                    product_info=product_info,
                    count=count,
                    style=style,
                    aspect_ratio="1:1",
                )

                # Upload generated images
                from .managers.upload_manager import UploadManager

                upload_manager = UploadManager(mcp_client=self.mcp_client)
                uploaded_creatives = []

                for i, image in enumerate(images):
                    try:
                        result = await upload_manager.upload_creative(
                            user_id=user_id,
                            image=image,
                            metadata={
                                "type": "reference_variation",
                                "reference_urls": reference_urls,
                                "style": style,
                                "prompt": prompt,
                            },
                        )
                        uploaded_creatives.append({
                            "creative_id": result.creative_id,
                            "url": result.url,
                            "created_at": result.created_at,
                        })
                    except Exception as e:
                        log.warning("upload_variation_failed", index=i, error=str(e))

                await upload_manager.close()

                # Deduct credits
                if uploaded_creatives:
                    actual_cost = len(uploaded_creatives) * 0.5
                    await self.mcp_client.call_tool(
                        "deduct_credit",
                        {
                            "user_id": user_id,
                            "credits": actual_cost,
                            "operation_type": "generate_from_reference",
                            "operation_id": f"ref_{user_id}_{len(uploaded_creatives)}",
                        },
                    )

                log.info(
                    "generate_from_reference_complete",
                    generated=len(uploaded_creatives),
                )

                return {
                    "status": "success",
                    "creative_ids": [c["creative_id"] for c in uploaded_creatives],
                    "creatives": uploaded_creatives,
                    "message": f"成功生成 {len(uploaded_creatives)} 张参考变体素材",
                }

            except ImageGenerationError as e:
                log.error("generate_from_reference_failed", error=str(e))
                return {
                    "status": "error",
                    "error": {
                        "code": "4003",
                        "type": "GENERATION_FAILED",
                        "message": f"图片生成失败: {e.message}",
                    },
                }

        except Exception as e:
            log.error("generate_from_reference_error", error=str(e))
            raise

    async def _generate_video(self, parameters: dict, context: dict) -> dict:
        """生成视频素材

        Generates video creatives using Google Veo models.
        Supports multiple generation modes:
        1. Text-to-video: Generate from prompt only
        2. Image-to-video: Generate from first frame image
        3. Video-to-video: Analyze reference video and generate similar
        4. Interpolation: Generate between first and last frames

        Args:
            parameters: {
                "prompt": str - Description of the video
                "mode": str - Generation mode: "text", "image", "video_reference", "interpolation"
                "first_frame_url": str - URL of first frame image (optional)
                "last_frame_url": str - URL of last frame image (for interpolation)
                "reference_video_url": str - URL of reference video (for video_reference mode)
                "duration": int - Video duration in seconds (4, 6, or 8)
                "aspect_ratio": str - Video aspect ratio (16:9 or 9:16)
                "negative_prompt": str - Things to avoid (optional)
                "use_fast_model": bool - Use faster model (optional)
                "wait_for_completion": bool - Wait for video to complete (default: False)
            }
            context: {"user_id": str, "session_id": str}

        Returns:
            Generated video result with operation_id for polling

        Requirements: Video generation capability using Veo
        """
        user_id = context.get("user_id")
        prompt = parameters.get("prompt", "")
        mode = parameters.get("mode", "text")
        first_frame_url = parameters.get("first_frame_url")
        last_frame_url = parameters.get("last_frame_url")
        reference_video_url = parameters.get("reference_video_url")
        duration = parameters.get("duration", 4)
        aspect_ratio = parameters.get("aspect_ratio", "16:9")
        negative_prompt = parameters.get("negative_prompt")
        use_fast_model = parameters.get("use_fast_model", False)
        wait_for_completion = parameters.get("wait_for_completion", False)

        log = logger.bind(
            user_id=user_id,
            mode=mode,
            prompt=prompt[:50] if prompt else None,
            duration=duration,
            aspect_ratio=aspect_ratio,
        )
        log.info("generate_video_start")

        # Validate parameters based on mode
        if mode == "text" and not prompt:
            return {
                "status": "error",
                "error": {
                    "code": "6006",
                    "type": "INVALID_PARAMS",
                    "message": "Please provide a prompt for text-to-video generation",
                },
            }

        if mode == "image" and not first_frame_url and not prompt:
            return {
                "status": "error",
                "error": {
                    "code": "6006",
                    "type": "INVALID_PARAMS",
                    "message": "Please provide a first frame image URL or prompt for image-to-video generation",
                },
            }

        if mode == "video_reference" and not reference_video_url:
            return {
                "status": "error",
                "error": {
                    "code": "6006",
                    "type": "INVALID_PARAMS",
                    "message": "Please provide a reference video URL for video-to-video generation",
                },
            }

        if mode == "interpolation" and (not first_frame_url or not last_frame_url):
            return {
                "status": "error",
                "error": {
                    "code": "6006",
                    "type": "INVALID_PARAMS",
                    "message": "Please provide both first and last frame URLs for interpolation",
                },
            }

        # Check credits (video generation costs more)
        video_credit_cost = duration * 2  # 2 credits per second
        try:
            await self.mcp_client.call_tool(
                "check_credit",
                {
                    "user_id": user_id,
                    "required_credits": video_credit_cost,
                    "operation_type": "generate_video",
                },
            )
        except MCPError as e:
            if "insufficient" in str(e).lower():
                return {
                    "status": "error",
                    "error": {
                        "code": "6011",
                        "type": "INSUFFICIENT_CREDITS",
                        "message": f"Credit 不足，视频生成需要 {video_credit_cost} credits ({duration}秒 x 2 credits/秒)",
                    },
                }
            raise

        try:
            # Import video generator
            from .generators.video_generator import VideoGenerator, VideoGenerationError

            generator = VideoGenerator(gemini_client=self.gemini_client)

            try:
                # Generate based on mode
                if mode == "text":
                    # Text-to-video generation
                    video = await generator.generate_from_prompt(
                        prompt=prompt,
                        duration=duration,
                        aspect_ratio=aspect_ratio,
                        negative_prompt=negative_prompt,
                        use_fast_model=use_fast_model,
                    )

                elif mode == "image":
                    # Image-to-video generation (first frame animation)
                    video = await generator.generate_from_image(
                        prompt=prompt or "Animate this image naturally",
                        first_frame_url=first_frame_url,
                        duration=duration,
                        aspect_ratio=aspect_ratio,
                        negative_prompt=negative_prompt,
                        use_fast_model=use_fast_model,
                    )

                elif mode == "video_reference":
                    # Video-to-video: analyze reference and generate similar
                    video = await generator.generate_from_video_reference(
                        video_url=reference_video_url,
                        custom_prompt=prompt,
                        duration=duration,
                        aspect_ratio=aspect_ratio,
                        use_fast_model=use_fast_model,
                    )

                elif mode == "interpolation":
                    # First/last frame interpolation
                    video = await generator.generate_with_interpolation(
                        prompt=prompt or "Smooth transition between frames",
                        first_frame_url=first_frame_url,
                        last_frame_url=last_frame_url,
                        duration=8,  # Interpolation requires 8s
                        aspect_ratio=aspect_ratio,
                        use_fast_model=use_fast_model,
                    )

                else:
                    return {
                        "status": "error",
                        "error": {
                            "code": "6006",
                            "type": "INVALID_PARAMS",
                            "message": f"Unknown video generation mode: {mode}. Supported: text, image, video_reference, interpolation",
                        },
                    }

                # Optionally wait for completion
                if wait_for_completion and video.operation_id:
                    log.info("waiting_for_video_completion", operation_id=video.operation_id)
                    result = await generator.wait_for_completion(
                        video.operation_id,
                        poll_interval=10,
                        max_wait=360,
                    )
                    video.status = result.get("status", "completed")
                    video.video_url = result.get("video_uri")

                    # Deduct credits on completion
                    await self.mcp_client.call_tool(
                        "deduct_credit",
                        {
                            "user_id": user_id,
                            "credits": video_credit_cost,
                            "operation_type": "generate_video",
                            "operation_id": video.operation_id,
                        },
                    )

                log.info(
                    "generate_video_started",
                    operation_id=video.operation_id,
                    status=video.status,
                )

                return {
                    "status": "success",
                    "video": video.to_dict(),
                    "message": "视频生成已启动" if video.status == "processing" else "视频生成完成",
                    "polling_info": {
                        "operation_id": video.operation_id,
                        "poll_endpoint": "/api/v1/video/status",
                        "estimated_time": f"{duration * 30}-{duration * 60} 秒",
                    } if video.status == "processing" else None,
                }

            except VideoGenerationError as e:
                log.error("generate_video_failed", error=str(e), code=e.code)
                return {
                    "status": "error",
                    "error": {
                        "code": e.code or "4003",
                        "type": "VIDEO_GENERATION_FAILED",
                        "message": f"视频生成失败: {e.message}",
                        "retryable": e.retryable,
                    },
                }

            finally:
                await generator.close()

        except Exception as e:
            log.error("generate_video_error", error=str(e), exc_info=True)
            raise

    async def _check_video_status(self, parameters: dict, context: dict) -> dict:
        """检查视频生成状态

        Checks the status of an ongoing video generation operation.

        Args:
            parameters: {
                "operation_id": str - The operation ID from generate_video
            }
            context: {"user_id": str, "session_id": str}

        Returns:
            Video generation status

        Requirements: Video generation capability
        """
        user_id = context.get("user_id")
        operation_id = parameters.get("operation_id")

        log = logger.bind(user_id=user_id, operation_id=operation_id)
        log.info("check_video_status_start")

        if not operation_id:
            return {
                "status": "error",
                "error": {
                    "code": "6006",
                    "type": "INVALID_PARAMS",
                    "message": "operation_id is required",
                },
            }

        try:
            from .generators.video_generator import VideoGenerator, VideoGenerationError

            generator = VideoGenerator(gemini_client=self.gemini_client)

            try:
                result = await generator.check_status(operation_id)

                log.info(
                    "check_video_status_complete",
                    status=result.get("status"),
                    has_video=result.get("video_uri") is not None,
                )

                # If completed, deduct credits
                if result.get("status") == "completed" and result.get("video_uri"):
                    # Get video duration from result or default to 4
                    duration = result.get("duration", 4)
                    video_credit_cost = duration * 2

                    try:
                        await self.mcp_client.call_tool(
                            "deduct_credit",
                            {
                                "user_id": user_id,
                                "credits": video_credit_cost,
                                "operation_type": "generate_video",
                                "operation_id": operation_id,
                            },
                        )
                    except MCPError as e:
                        log.warning("credit_deduction_failed", error=str(e))

                return {
                    "status": "success",
                    "video_status": result.get("status"),
                    "video_url": result.get("video_uri"),
                    "progress": result.get("progress"),
                    "message": self._get_status_message(result.get("status")),
                }

            except VideoGenerationError as e:
                log.error("check_video_status_failed", error=str(e), code=e.code)
                return {
                    "status": "error",
                    "error": {
                        "code": e.code or "4003",
                        "type": "VIDEO_STATUS_CHECK_FAILED",
                        "message": f"状态查询失败: {e.message}",
                    },
                }

            finally:
                await generator.close()

        except Exception as e:
            log.error("check_video_status_error", error=str(e), exc_info=True)
            raise

    def _get_status_message(self, status: str | None) -> str:
        """Get user-friendly status message."""
        messages = {
            "processing": "视频正在生成中，请稍候...",
            "completed": "视频生成完成！",
            "failed": "视频生成失败",
            None: "状态未知",
        }
        return messages.get(status, f"状态: {status}")
