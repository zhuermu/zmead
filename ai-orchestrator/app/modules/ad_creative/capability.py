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
        "analyze_creative",
        "score_creative",
        "generate_variants",
        "analyze_competitor",
        "get_creatives",
        "delete_creative",
        "download_creative",
        "batch_download",
        "upload_reference",
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

        Args:
            parameters: {
                "file_data": bytes,
                "file_name": str,
                "file_type": str
            }
            context: {"user_id": str, "session_id": str}

        Returns:
            Upload result

        Requirements: 2.1, 2.2, 2.3, 2.5
        """
        logger.info("upload_reference_stub", parameters=parameters)

        # TODO: Implement in task 3 (file validation and upload)
        return {
            "status": "success",
            "message": "Reference upload not yet implemented (task 3)",
        }
