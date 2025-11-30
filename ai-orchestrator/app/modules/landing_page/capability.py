"""
Landing Page capability - Main entry point for the module.

This module provides the main entry point for Landing Page functionality,
including product extraction, page generation, optimization, translation,
A/B testing, hosting, and export.

Requirements: 1.1, 2.1, 3.1, 4.1, 5.1, 6.1, 7.1, 8.1, 9.1, 1.5, 4.5
"""

import structlog
from redis.asyncio import Redis

from app.core.errors import ErrorHandler as CoreErrorHandler
from app.services.gemini_client import GeminiClient, GeminiError
from app.services.mcp_client import MCPClient, MCPError

from .utils import ErrorHandler as LPErrorHandler, ErrorCode

logger = structlog.get_logger(__name__)


class LandingPage:
    """Landing Page 功能模块主入口

    Provides comprehensive landing page capabilities including:
    - Product information extraction (Shopify, Amazon)
    - AI-powered landing page generation
    - Copy optimization (Gemini 2.5 Pro)
    - Multi-language translation (Gemini 2.5 Flash)
    - A/B testing with chi-square analysis
    - Landing page hosting (S3 + CloudFront)
    - Landing page export
    - Conversion tracking (Facebook Pixel + internal)

    Requirements: 1.1, 2.1, 3.1, 4.1, 5.1, 6.1, 7.1, 8.1, 9.1
    """

    # Supported actions for routing
    SUPPORTED_ACTIONS = [
        "parse_product",
        "generate_landing_page",
        "update_landing_page",
        "optimize_copy",
        "translate_landing_page",
        "create_ab_test",
        "analyze_ab_test",
        "publish_landing_page",
        "export_landing_page",
    ]

    def __init__(
        self,
        mcp_client: MCPClient | None = None,
        gemini_client: GeminiClient | None = None,
        redis_client: Redis | None = None,
        config: dict | None = None,
    ):
        """初始化 Landing Page 模块

        Args:
            mcp_client: MCP client for Web Platform communication
            gemini_client: Gemini client for AI generation and analysis
            redis_client: Redis client for caching
            config: Configuration dictionary (optional)
        """
        self.mcp_client = mcp_client or MCPClient()
        self.gemini_client = gemini_client or GeminiClient()
        self.redis_client = redis_client
        self.config = config or {}
        self.error_handler = LPErrorHandler()

        logger.info(
            "landing_page_initialized",
            has_mcp=self.mcp_client is not None,
            has_gemini=self.gemini_client is not None,
            has_redis=self.redis_client is not None,
        )

    async def execute(self, action: str, parameters: dict, context: dict) -> dict:
        """
        执行落地页生成操作

        Implements action routing with comprehensive error handling and logging.
        All errors are caught and converted to structured error responses.

        Args:
            action: 操作名称 (parse_product, generate_landing_page, etc.)
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

        log.info("landing_page_execute_start", parameters=parameters)

        try:
            # Route to appropriate handler
            if action == "parse_product":
                result = await self._parse_product(parameters, context)
            elif action == "generate_landing_page":
                result = await self._generate_landing_page(parameters, context)
            elif action == "update_landing_page":
                result = await self._update_landing_page(parameters, context)
            elif action == "optimize_copy":
                result = await self._optimize_copy(parameters, context)
            elif action == "translate_landing_page":
                result = await self._translate_landing_page(parameters, context)
            elif action == "create_ab_test":
                result = await self._create_ab_test(parameters, context)
            elif action == "analyze_ab_test":
                result = await self._analyze_ab_test(parameters, context)
            elif action == "publish_landing_page":
                result = await self._publish_landing_page(parameters, context)
            elif action == "export_landing_page":
                result = await self._export_landing_page(parameters, context)
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

            log.info("landing_page_execute_success", action=action)
            return result

        except (MCPError, GeminiError) as e:
            # Handle known service errors
            log.error(
                "landing_page_service_error",
                error=str(e),
                error_type=type(e).__name__,
            )
            error_state = ErrorHandler.handle_error(
                error=e,
                context=f"landing_page.{action}",
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
                "landing_page_unexpected_error",
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )
            error_state = ErrorHandler.handle_error(
                error=e,
                context=f"landing_page.{action}",
                user_id=user_id,
                session_id=session_id,
            )
            return {
                "status": "error",
                **error_state,
            }

    async def _parse_product(self, parameters: dict, context: dict) -> dict:
        """解析产品信息

        Extracts product information from e-commerce platform URLs.
        Auto-selects the correct extractor based on URL pattern.

        Args:
            parameters: {
                "product_url": str,
                "platform": "shopify" | "amazon" (optional, auto-detected)
            }
            context: {"user_id": str, "session_id": str}

        Returns:
            ProductInfo data

        Requirements: 1.1, 1.2, 1.3, 1.4, 1.5
        """
        from .extractors import get_extractor_router, ExtractorError, UnsupportedURLError

        product_url = parameters.get("product_url")
        if not product_url:
            return {
                "status": "error",
                "error": {
                    "code": "6006",
                    "type": "PRODUCT_URL_INVALID",
                    "message": "Product URL is required",
                },
            }

        logger.info("parse_product_start", url=product_url)

        router = get_extractor_router()

        try:
            # Extract product information using the appropriate extractor
            product_info = await router.extract(product_url)

            logger.info(
                "parse_product_success",
                url=product_url,
                title=product_info.title,
                platform=product_info.source,
            )

            return {
                "status": "success",
                "product_info": product_info.model_dump(),
                "message": f"Successfully extracted product info from {product_info.source}",
            }

        except UnsupportedURLError as e:
            logger.warning("parse_product_unsupported_url", url=product_url)
            return {
                "status": "error",
                "error": {
                    "code": e.code,
                    "type": "PRODUCT_URL_INVALID",
                    "message": e.message,
                    "suggestion": "Please provide a valid Shopify or Amazon product URL",
                },
            }

        except ExtractorError as e:
            logger.error("parse_product_extraction_failed", url=product_url, error=str(e))
            return {
                "status": "error",
                "error": {
                    "code": e.code or "6007",
                    "type": "PRODUCT_INFO_EXTRACTION_FAILED",
                    "message": e.message,
                    "suggestion": "Please check the URL is accessible or try again later",
                },
            }

    async def _generate_landing_page(
        self, parameters: dict, context: dict
    ) -> dict:
        """生成落地页

        Generates a landing page from product information.

        Args:
            parameters: {
                "product_info": dict,
                "template": "modern" | "minimal" | "vibrant",
                "language": str,
                "pixel_id": str (optional)
            }
            context: {"user_id": str, "session_id": str}

        Returns:
            LandingPageContent data

        Requirements: 2.1, 2.2, 2.3, 2.4, 2.5
        """
        from .generators import PageGenerator
        from .tracking import PixelInjector
        from .models import ProductInfo

        product_info_dict = parameters.get("product_info")
        if not product_info_dict:
            return {
                "status": "error",
                "error": {
                    "code": "4003",
                    "type": "GENERATION_FAILED",
                    "message": "Product information is required",
                },
            }

        template = parameters.get("template", "modern")
        language = parameters.get("language", "en")
        pixel_id = parameters.get("pixel_id")

        logger.info(
            "generate_landing_page_start",
            template=template,
            language=language,
            has_pixel=pixel_id is not None,
        )

        try:
            # Parse product info
            product_info = ProductInfo(**product_info_dict)

            # Initialize generator
            page_generator = PageGenerator(gemini_client=self.gemini_client)

            # Generate landing page content
            landing_page = await page_generator.generate(
                product_info=product_info,
                template=template,
                language=language,
                pixel_id=pixel_id,
            )

            # Prepare sections for response
            sections = {
                "hero": {
                    "headline": landing_page.hero.headline,
                    "subheadline": landing_page.hero.subheadline,
                    "image": str(landing_page.hero.image),
                    "cta_text": landing_page.hero.cta_text,
                },
                "features": [
                    {
                        "title": f.title,
                        "description": f.description,
                        "icon": f.icon,
                    }
                    for f in landing_page.features
                ],
                "reviews": [
                    {
                        "rating": r.rating,
                        "text": r.text,
                    }
                    for r in landing_page.reviews
                ],
                "faq": [
                    {
                        "question": faq.question,
                        "answer": faq.answer,
                    }
                    for faq in landing_page.faq
                ],
                "cta": {
                    "text": landing_page.cta.text,
                    "url": str(landing_page.cta.url),
                },
            }

            # Generate placeholder URL (actual hosting in task 12)
            user_id = context.get("user_id", "user")
            url = f"https://{user_id}.aae-pages.com/{landing_page.landing_page_id}"

            # Save to Web Platform via MCP
            try:
                await self.mcp_client.call_tool(
                    "create_landing_page",
                    {
                        "user_id": context.get("user_id"),
                        "landing_page_data": {
                            "landing_page_id": landing_page.landing_page_id,
                            "title": product_info.title,
                            "url": url,
                            "template": template,
                            "status": "draft",
                            "sections": sections,
                        },
                    },
                )
            except Exception as e:
                # Log but don't fail - MCP save is not critical for generation
                logger.warning(
                    "mcp_save_failed",
                    error=str(e),
                    landing_page_id=landing_page.landing_page_id,
                )

            logger.info(
                "generate_landing_page_complete",
                landing_page_id=landing_page.landing_page_id,
                feature_count=len(landing_page.features),
                review_count=len(landing_page.reviews),
            )

            return {
                "status": "success",
                "landing_page_id": landing_page.landing_page_id,
                "url": url,
                "sections": sections,
                "message": "落地页生成成功",
            }

        except Exception as e:
            logger.error(
                "generate_landing_page_failed",
                error=str(e),
                exc_info=True,
            )
            return {
                "status": "error",
                "error": {
                    "code": "4003",
                    "type": "GENERATION_FAILED",
                    "message": f"Failed to generate landing page: {str(e)}",
                    "retry_allowed": True,
                },
            }

    async def _update_landing_page(
        self, parameters: dict, context: dict
    ) -> dict:
        """更新落地页

        Updates specific fields of an existing landing page.

        Args:
            parameters: {
                "landing_page_id": str,
                "updates": dict (field_path -> value)
            }
            context: {"user_id": str, "session_id": str}

        Returns:
            Updated fields list and new URL

        Requirements: 3.1, 3.2, 3.3, 3.4, 3.5
        """
        from .managers import UpdateHandler, InvalidFieldPathError

        landing_page_id = parameters.get("landing_page_id")
        updates = parameters.get("updates", {})

        if not landing_page_id:
            return {
                "status": "error",
                "error": {
                    "code": "5000",
                    "type": "DATA_NOT_FOUND",
                    "message": "Landing page ID is required",
                },
            }

        if not updates:
            return {
                "status": "error",
                "error": {
                    "code": "1001",
                    "type": "INVALID_PARAMETERS",
                    "message": "No updates provided",
                },
            }

        logger.info(
            "update_landing_page_start",
            landing_page_id=landing_page_id,
            update_count=len(updates),
        )

        try:
            # Fetch current landing page data from Web Platform
            try:
                landing_page_response = await self.mcp_client.call_tool(
                    "get_landing_page",
                    {
                        "user_id": context.get("user_id"),
                        "landing_page_id": landing_page_id,
                    },
                )
                landing_page_data = landing_page_response.get("landing_page", {})
            except Exception as e:
                logger.warning(
                    "mcp_get_landing_page_failed",
                    error=str(e),
                    landing_page_id=landing_page_id,
                )
                # For now, return error if we can't fetch the landing page
                return {
                    "status": "error",
                    "error": {
                        "code": "5000",
                        "type": "DATA_NOT_FOUND",
                        "message": f"Landing page '{landing_page_id}' not found",
                    },
                }

            # Initialize update handler
            update_handler = UpdateHandler()

            # Apply updates
            updated_data, updated_fields = update_handler.apply_updates(
                landing_page_data, updates
            )

            # Generate URL
            user_id = context.get("user_id", "user")
            url = f"https://{user_id}.aae-pages.com/{landing_page_id}"

            # Save updated landing page to Web Platform
            try:
                await self.mcp_client.call_tool(
                    "update_landing_page",
                    {
                        "user_id": context.get("user_id"),
                        "landing_page_id": landing_page_id,
                        "updates": updated_data,
                    },
                )
            except Exception as e:
                logger.warning(
                    "mcp_update_landing_page_failed",
                    error=str(e),
                    landing_page_id=landing_page_id,
                )
                # Continue - the update was applied locally

            logger.info(
                "update_landing_page_complete",
                landing_page_id=landing_page_id,
                updated_fields=updated_fields,
            )

            return {
                "status": "success",
                "landing_page_id": landing_page_id,
                "updated_fields": updated_fields,
                "url": url,
                "message": "落地页已更新",
            }

        except InvalidFieldPathError as e:
            logger.warning(
                "update_landing_page_invalid_field",
                error=str(e),
                field_path=e.field_path,
            )
            return {
                "status": "error",
                "error": {
                    "code": "1001",
                    "type": "INVALID_FIELD_PATH",
                    "message": e.message,
                    "field_path": e.field_path,
                },
            }

        except Exception as e:
            logger.error(
                "update_landing_page_failed",
                error=str(e),
                exc_info=True,
            )
            return {
                "status": "error",
                "error": {
                    "code": "5001",
                    "type": "UPDATE_FAILED",
                    "message": f"Failed to update landing page: {str(e)}",
                    "retry_allowed": True,
                },
            }

    async def _optimize_copy(self, parameters: dict, context: dict) -> dict:
        """优化文案

        Optimizes landing page copy using AI (Gemini 2.5 Pro).

        Args:
            parameters: {
                "landing_page_id": str (optional),
                "section": str (hero, cta, features, subheadline, description),
                "current_text": str,
                "optimization_goal": str (increase_conversion, emotional_appeal, etc.)
            }
            context: {"user_id": str, "session_id": str}

        Returns:
            OptimizationResult data with optimized_text, improvements, confidence_score

        Requirements: 4.1, 4.2, 4.3, 4.4, 4.5
        """
        from .optimizers import CopyOptimizer

        current_text = parameters.get("current_text")
        section = parameters.get("section", "hero")
        optimization_goal = parameters.get("optimization_goal", "increase_conversion")

        if not current_text:
            return {
                "status": "error",
                "error": {
                    "code": "1001",
                    "type": "INVALID_PARAMETERS",
                    "message": "current_text is required for copy optimization",
                },
            }

        logger.info(
            "optimize_copy_start",
            section=section,
            optimization_goal=optimization_goal,
            text_length=len(current_text),
        )

        # Initialize copy optimizer with the module's Gemini client
        copy_optimizer = CopyOptimizer(gemini_client=self.gemini_client)

        # Build context for optimization (optional product info)
        optimization_context = None
        landing_page_id = parameters.get("landing_page_id")
        if landing_page_id:
            try:
                # Try to fetch landing page data for context
                landing_page_response = await self.mcp_client.call_tool(
                    "get_landing_page",
                    {
                        "user_id": context.get("user_id"),
                        "landing_page_id": landing_page_id,
                    },
                )
                landing_page_data = landing_page_response.get("landing_page", {})
                if landing_page_data:
                    optimization_context = {"product_info": landing_page_data}
            except Exception as e:
                # Context is optional, continue without it
                logger.debug(
                    "optimize_copy_context_fetch_failed",
                    error=str(e),
                    landing_page_id=landing_page_id,
                )

        # Perform optimization
        result = await copy_optimizer.optimize(
            current_text=current_text,
            section=section,
            optimization_goal=optimization_goal,
            context=optimization_context,
        )

        logger.info(
            "optimize_copy_complete",
            fallback=result.fallback,
            improvements_count=len(result.improvements),
            confidence_score=result.confidence_score,
        )

        return {
            "status": "success",
            "optimized_text": result.optimized_text,
            "improvements": result.improvements,
            "confidence_score": result.confidence_score,
            "fallback": result.fallback,
            "message": "文案优化完成" if not result.fallback else "优化失败，返回原文案",
        }

    async def _translate_landing_page(
        self, parameters: dict, context: dict
    ) -> dict:
        """翻译落地页

        Translates landing page content to target language while preserving
        the original structure and format. Generates a new language version URL.

        Args:
            parameters: {
                "landing_page_id": str,
                "target_language": str,
                "sections_to_translate": list[str] (optional)
            }
            context: {"user_id": str, "session_id": str}

        Returns:
            TranslationResult data with translated content, new ID, and URL

        Requirements: 5.1, 5.2, 5.3, 5.4, 5.5
        """
        from .optimizers.translator import (
            Translator,
            TranslationError,
            UnsupportedLanguageError,
        )

        landing_page_id = parameters.get("landing_page_id")
        target_language = parameters.get("target_language")
        sections_to_translate = parameters.get("sections_to_translate")

        # Validate required parameters
        if not landing_page_id:
            return {
                "status": "error",
                "error": {
                    "code": "5000",
                    "type": "DATA_NOT_FOUND",
                    "message": "Landing page ID is required",
                },
            }

        if not target_language:
            return {
                "status": "error",
                "error": {
                    "code": "1001",
                    "type": "INVALID_PARAMETERS",
                    "message": "Target language is required",
                },
            }

        logger.info(
            "translate_landing_page_start",
            landing_page_id=landing_page_id,
            target_language=target_language,
            sections=sections_to_translate,
        )

        # Initialize translator
        translator = Translator(gemini_client=self.gemini_client)

        # Validate target language early
        if not translator.is_language_supported(target_language):
            logger.warning(
                "translate_landing_page_unsupported_language",
                language=target_language,
            )
            return {
                "status": "error",
                "error": {
                    "code": "UNSUPPORTED_LANGUAGE",
                    "type": "TRANSLATION_ERROR",
                    "message": f"Unsupported language: {target_language}",
                    "supported_languages": list(translator.get_supported_languages().keys()),
                },
            }

        # Fetch landing page content from Web Platform
        try:
            landing_page_response = await self.mcp_client.call_tool(
                "get_landing_page",
                {
                    "user_id": context.get("user_id"),
                    "landing_page_id": landing_page_id,
                },
            )
            landing_page_data = landing_page_response.get("landing_page", {})
            
            if not landing_page_data:
                return {
                    "status": "error",
                    "error": {
                        "code": "5000",
                        "type": "DATA_NOT_FOUND",
                        "message": f"Landing page '{landing_page_id}' not found",
                    },
                }
        except Exception as e:
            logger.warning(
                "mcp_get_landing_page_failed",
                error=str(e),
                landing_page_id=landing_page_id,
            )
            return {
                "status": "error",
                "error": {
                    "code": "5000",
                    "type": "DATA_NOT_FOUND",
                    "message": f"Failed to fetch landing page '{landing_page_id}': {str(e)}",
                },
            }

        # Extract sections content for translation
        # The content to translate is typically in the 'sections' field
        content_to_translate = landing_page_data.get("sections", landing_page_data)
        source_language = landing_page_data.get("language", "en")
        user_id = context.get("user_id", "user")

        try:
            # Translate the landing page content
            translation_result = await translator.translate_landing_page(
                landing_page_id=landing_page_id,
                content=content_to_translate,
                target_language=target_language,
                sections=sections_to_translate,
                source_language=source_language,
                user_id=user_id,
            )

            # Save translated landing page to Web Platform
            try:
                await self.mcp_client.call_tool(
                    "create_landing_page",
                    {
                        "user_id": user_id,
                        "landing_page_data": {
                            "landing_page_id": translation_result.translated_landing_page_id,
                            "title": landing_page_data.get("title", ""),
                            "url": str(translation_result.url),
                            "template": landing_page_data.get("template", "modern"),
                            "language": target_language,
                            "status": "draft",
                            "sections": translation_result.translations,
                            "source_landing_page_id": landing_page_id,
                        },
                    },
                )
            except Exception as e:
                # Log but don't fail - MCP save is not critical
                logger.warning(
                    "mcp_save_translated_landing_page_failed",
                    error=str(e),
                    translated_landing_page_id=translation_result.translated_landing_page_id,
                )

            logger.info(
                "translate_landing_page_success",
                landing_page_id=landing_page_id,
                translated_landing_page_id=translation_result.translated_landing_page_id,
                target_language=target_language,
            )

            return {
                "status": "success",
                "translated_landing_page_id": translation_result.translated_landing_page_id,
                "url": str(translation_result.url),
                "translations": translation_result.translations,
                "source_language": translation_result.source_language,
                "target_language": translation_result.target_language,
                "message": "翻译完成",
            }

        except UnsupportedLanguageError as e:
            logger.warning(
                "translate_landing_page_unsupported_language",
                language=e.language,
            )
            return {
                "status": "error",
                "error": {
                    "code": e.code,
                    "type": "TRANSLATION_ERROR",
                    "message": e.message,
                    "supported_languages": list(translator.get_supported_languages().keys()),
                },
            }

        except TranslationError as e:
            logger.error(
                "translate_landing_page_translation_error",
                error=str(e),
                error_code=e.code,
            )
            return {
                "status": "error",
                "error": {
                    "code": e.code,
                    "type": "TRANSLATION_ERROR",
                    "message": e.message,
                    "retryable": e.retryable,
                },
            }

        except Exception as e:
            logger.error(
                "translate_landing_page_unexpected_error",
                error=str(e),
                exc_info=True,
            )
            return {
                "status": "error",
                "error": {
                    "code": "TRANSLATION_ERROR",
                    "type": "TRANSLATION_ERROR",
                    "message": f"Translation failed: {str(e)}",
                    "retryable": False,
                },
            }

    async def _create_ab_test(self, parameters: dict, context: dict) -> dict:
        """创建 A/B 测试

        Creates an A/B test with multiple variants.

        Args:
            parameters: {
                "test_name": str,
                "landing_page_id": str,
                "variants": list[dict],
                "traffic_split": list[int],
                "duration_days": int
            }
            context: {"user_id": str, "session_id": str}

        Returns:
            ABTest data with variant URLs

        Requirements: 6.1, 6.2
        """
        from .managers import ABTestManager

        test_name = parameters.get("test_name")
        landing_page_id = parameters.get("landing_page_id")
        variants = parameters.get("variants", [])
        traffic_split = parameters.get("traffic_split", [])
        duration_days = parameters.get("duration_days", 7)

        # Validate required parameters
        if not test_name:
            return {
                "status": "error",
                "error": {
                    "code": "1001",
                    "type": "INVALID_PARAMETERS",
                    "message": "test_name is required",
                },
            }

        if not landing_page_id:
            return {
                "status": "error",
                "error": {
                    "code": "1001",
                    "type": "INVALID_PARAMETERS",
                    "message": "landing_page_id is required",
                },
            }

        if not variants or len(variants) < 2:
            return {
                "status": "error",
                "error": {
                    "code": "1001",
                    "type": "INVALID_PARAMETERS",
                    "message": "At least 2 variants are required for A/B testing",
                },
            }

        # Default traffic split if not provided
        if not traffic_split:
            # Equal split among variants
            split_per_variant = 100 // len(variants)
            traffic_split = [split_per_variant] * len(variants)
            # Adjust last variant to ensure sum is 100
            traffic_split[-1] = 100 - sum(traffic_split[:-1])

        logger.info(
            "create_ab_test_start",
            test_name=test_name,
            landing_page_id=landing_page_id,
            num_variants=len(variants),
            traffic_split=traffic_split,
            duration_days=duration_days,
        )

        try:
            # Initialize A/B test manager
            ab_test_manager = ABTestManager(
                mcp_client=self.mcp_client,
                redis_client=self.redis_client,
            )

            # Create the A/B test
            result = await ab_test_manager.create_test(
                test_name=test_name,
                landing_page_id=landing_page_id,
                variants=variants,
                traffic_split=traffic_split,
                duration_days=duration_days,
                context=context,
            )

            logger.info(
                "create_ab_test_success",
                test_id=result.get("test_id"),
                num_variant_urls=len(result.get("variant_urls", [])),
            )

            return result

        except ValueError as e:
            logger.warning(
                "create_ab_test_validation_error",
                error=str(e),
            )
            return {
                "status": "error",
                "error": {
                    "code": "1001",
                    "type": "INVALID_PARAMETERS",
                    "message": str(e),
                },
            }

        except Exception as e:
            logger.error(
                "create_ab_test_failed",
                error=str(e),
                exc_info=True,
            )
            return {
                "status": "error",
                "error": {
                    "code": "AB_TEST_CREATION_FAILED",
                    "type": "AB_TEST_ERROR",
                    "message": f"Failed to create A/B test: {str(e)}",
                    "retry_allowed": True,
                },
            }

    async def _analyze_ab_test(self, parameters: dict, context: dict) -> dict:
        """分析 A/B 测试结果

        Analyzes A/B test results using chi-square test.

        Args:
            parameters: {
                "test_id": str
            }
            context: {"user_id": str, "session_id": str}

        Returns:
            ABTestAnalysis data with winner and recommendations

        Requirements: 6.3, 6.4, 6.5, 6.6
        """
        from .managers import ABTestManager

        test_id = parameters.get("test_id")

        if not test_id:
            return {
                "status": "error",
                "error": {
                    "code": "1001",
                    "type": "INVALID_PARAMETERS",
                    "message": "test_id is required",
                },
            }

        logger.info(
            "analyze_ab_test_start",
            test_id=test_id,
        )

        try:
            # Initialize A/B test manager
            ab_test_manager = ABTestManager(
                mcp_client=self.mcp_client,
                redis_client=self.redis_client,
            )

            # Analyze the A/B test
            analysis = await ab_test_manager.analyze_test(
                test_id=test_id,
                context=context,
            )

            # Convert results to serializable format
            results = [
                {
                    "variant": r.variant,
                    "visits": r.visits,
                    "conversions": r.conversions,
                    "conversion_rate": r.conversion_rate,
                }
                for r in analysis.results
            ]

            # Convert winner to serializable format
            winner = None
            if analysis.winner:
                winner = {
                    "variant": analysis.winner.variant,
                    "confidence": analysis.winner.confidence,
                    "improvement": analysis.winner.improvement,
                }

            logger.info(
                "analyze_ab_test_success",
                test_id=test_id,
                has_winner=winner is not None,
                is_significant=analysis.is_significant,
            )

            return {
                "status": "success",
                "test_id": analysis.test_id,
                "results": results,
                "winner": winner,
                "recommendation": analysis.recommendation,
                "is_significant": analysis.is_significant,
                "p_value": analysis.p_value,
                "message": (
                    f"测试分析完成。{'找到获胜变体' if winner else '差异不显著'}"
                ),
            }

        except ValueError as e:
            logger.warning(
                "analyze_ab_test_not_found",
                test_id=test_id,
                error=str(e),
            )
            return {
                "status": "error",
                "error": {
                    "code": "5000",
                    "type": "DATA_NOT_FOUND",
                    "message": str(e),
                },
            }

        except Exception as e:
            logger.error(
                "analyze_ab_test_failed",
                test_id=test_id,
                error=str(e),
                exc_info=True,
            )
            return {
                "status": "error",
                "error": {
                    "code": "AB_TEST_ANALYSIS_FAILED",
                    "type": "AB_TEST_ERROR",
                    "message": f"Failed to analyze A/B test: {str(e)}",
                    "retry_allowed": True,
                },
            }

    async def _publish_landing_page(
        self, parameters: dict, context: dict
    ) -> dict:
        """发布落地页

        Publishes landing page to S3 and CloudFront.

        Args:
            parameters: {
                "landing_page_id": str,
                "custom_domain": str (optional)
            }
            context: {"user_id": str, "session_id": str}

        Returns:
            PublishResult data with URLs and SSL status

        Requirements: 7.1, 7.2, 7.3, 7.4, 7.5
        """
        from .managers import HostingManager
        from .generators import PageGenerator
        from .tracking import DualTracker

        landing_page_id = parameters.get("landing_page_id")
        custom_domain = parameters.get("custom_domain")

        if not landing_page_id:
            return {
                "status": "error",
                "error": {
                    "code": "5000",
                    "type": "DATA_NOT_FOUND",
                    "message": "Landing page ID is required",
                },
            }

        user_id = context.get("user_id")
        if not user_id:
            return {
                "status": "error",
                "error": {
                    "code": "UNAUTHORIZED",
                    "type": "AUTHENTICATION_ERROR",
                    "message": "User ID is required",
                },
            }

        logger.info(
            "publish_landing_page_start",
            landing_page_id=landing_page_id,
            custom_domain=custom_domain,
        )

        try:
            # Fetch landing page data from Web Platform
            try:
                landing_page_response = await self.mcp_client.call_tool(
                    "get_landing_page",
                    {
                        "user_id": user_id,
                        "landing_page_id": landing_page_id,
                    },
                )
                landing_page_data = landing_page_response.get("landing_page", {})
                
                if not landing_page_data:
                    return {
                        "status": "error",
                        "error": {
                            "code": "5000",
                            "type": "DATA_NOT_FOUND",
                            "message": f"Landing page '{landing_page_id}' not found",
                        },
                    }
            except Exception as e:
                logger.error(
                    "mcp_get_landing_page_failed",
                    error=str(e),
                    landing_page_id=landing_page_id,
                )
                return {
                    "status": "error",
                    "error": {
                        "code": "5000",
                        "type": "DATA_NOT_FOUND",
                        "message": f"Failed to fetch landing page: {str(e)}",
                    },
                }

            # Generate HTML content from landing page data
            page_generator = PageGenerator(gemini_client=self.gemini_client)
            html_content = await page_generator.render_html(
                landing_page_data=landing_page_data,
                template=landing_page_data.get("template", "modern"),
            )

            # Inject dual tracking (Facebook Pixel + Internal tracking)
            pixel_id = landing_page_data.get("pixel_id")
            campaign_id = landing_page_data.get("campaign_id")
            
            dual_tracker = DualTracker(api_base_url=self.config.get("api_base_url", ""))
            html_content = dual_tracker.inject_dual_tracking(
                html=html_content,
                landing_page_id=landing_page_id,
                pixel_id=pixel_id,
                campaign_id=campaign_id,
                events=["PageView", "AddToCart", "Purchase"],
            )

            # Initialize hosting manager
            hosting_manager = HostingManager(mcp_client=self.mcp_client)

            # Publish landing page
            result = await hosting_manager.publish(
                landing_page_id=landing_page_id,
                html_content=html_content,
                user_id=user_id,
                custom_domain=custom_domain,
            )

            # Update landing page status to published
            try:
                await self.mcp_client.call_tool(
                    "update_landing_page",
                    {
                        "user_id": user_id,
                        "landing_page_id": landing_page_id,
                        "updates": {
                            "status": "published",
                            "url": str(result.url),
                            "cdn_url": str(result.cdn_url),
                        },
                    },
                )
            except Exception as e:
                # Log but don't fail - status update is not critical
                logger.warning(
                    "mcp_update_status_failed",
                    error=str(e),
                    landing_page_id=landing_page_id,
                )

            logger.info(
                "publish_landing_page_success",
                landing_page_id=landing_page_id,
                url=str(result.url),
                ssl_status=result.ssl_status,
            )

            return {
                "status": "success",
                "landing_page_id": result.landing_page_id,
                "url": str(result.url),
                "cdn_url": str(result.cdn_url),
                "ssl_status": result.ssl_status,
                "custom_domain": result.custom_domain,
                "message": "落地页已发布",
            }

        except MCPError as e:
            logger.error(
                "publish_landing_page_mcp_error",
                error=str(e),
                error_code=e.code,
            )
            return {
                "status": "error",
                "error": {
                    "code": e.code or "PUBLISH_FAILED",
                    "type": "HOSTING_ERROR",
                    "message": e.message or f"Failed to publish landing page: {str(e)}",
                    "retry_allowed": True,
                },
            }

        except Exception as e:
            logger.error(
                "publish_landing_page_failed",
                error=str(e),
                exc_info=True,
            )
            return {
                "status": "error",
                "error": {
                    "code": "PUBLISH_FAILED",
                    "type": "HOSTING_ERROR",
                    "message": f"Failed to publish landing page: {str(e)}",
                    "retry_allowed": True,
                },
            }

    async def _export_landing_page(
        self, parameters: dict, context: dict
    ) -> dict:
        """导出落地页

        Exports landing page as downloadable ZIP file.

        Args:
            parameters: {
                "landing_page_id": str,
                "format": "html"
            }
            context: {"user_id": str, "session_id": str}

        Returns:
            ExportResult data with download URL

        Requirements: 8.1, 8.2, 8.3, 8.4, 8.5
        """
        from .managers import ExportManager
        from .generators import PageGenerator
        from .tracking import DualTracker

        landing_page_id = parameters.get("landing_page_id")
        export_format = parameters.get("format", "html")

        if not landing_page_id:
            return {
                "status": "error",
                "error": {
                    "code": "5000",
                    "type": "DATA_NOT_FOUND",
                    "message": "Landing page ID is required",
                },
            }

        if export_format != "html":
            return {
                "status": "error",
                "error": {
                    "code": "1001",
                    "type": "INVALID_PARAMETERS",
                    "message": f"Unsupported export format: {export_format}. Only 'html' is supported.",
                },
            }

        user_id = context.get("user_id")
        if not user_id:
            return {
                "status": "error",
                "error": {
                    "code": "UNAUTHORIZED",
                    "type": "AUTHENTICATION_ERROR",
                    "message": "User ID is required",
                },
            }

        logger.info(
            "export_landing_page_start",
            landing_page_id=landing_page_id,
            format=export_format,
        )

        try:
            # Fetch landing page data from Web Platform
            try:
                landing_page_response = await self.mcp_client.call_tool(
                    "get_landing_page",
                    {
                        "user_id": user_id,
                        "landing_page_id": landing_page_id,
                    },
                )
                landing_page_data = landing_page_response.get("landing_page", {})
                
                if not landing_page_data:
                    return {
                        "status": "error",
                        "error": {
                            "code": "5000",
                            "type": "DATA_NOT_FOUND",
                            "message": f"Landing page '{landing_page_id}' not found",
                        },
                    }
            except Exception as e:
                logger.error(
                    "mcp_get_landing_page_failed",
                    error=str(e),
                    landing_page_id=landing_page_id,
                )
                return {
                    "status": "error",
                    "error": {
                        "code": "5000",
                        "type": "DATA_NOT_FOUND",
                        "message": f"Failed to fetch landing page: {str(e)}",
                    },
                }

            # Generate HTML content from landing page data
            page_generator = PageGenerator(gemini_client=self.gemini_client)
            html_content = await page_generator.render_html(
                landing_page_data=landing_page_data,
                template=landing_page_data.get("template", "modern"),
            )

            # Inject dual tracking (Facebook Pixel + Internal tracking)
            pixel_id = landing_page_data.get("pixel_id")
            campaign_id = landing_page_data.get("campaign_id")
            
            dual_tracker = DualTracker(api_base_url=self.config.get("api_base_url", ""))
            html_content = dual_tracker.inject_dual_tracking(
                html=html_content,
                landing_page_id=landing_page_id,
                pixel_id=pixel_id,
                campaign_id=campaign_id,
                events=["PageView", "AddToCart", "Purchase"],
            )

            # Initialize export manager
            export_manager = ExportManager(mcp_client=self.mcp_client)

            # Export landing page
            result = await export_manager.export(
                landing_page_id=landing_page_id,
                html_content=html_content,
                user_id=user_id,
                format=export_format,
            )

            logger.info(
                "export_landing_page_success",
                landing_page_id=landing_page_id,
                file_size=result.file_size,
                expires_at=result.expires_at,
            )

            return {
                "status": "success",
                "download_url": str(result.download_url),
                "expires_at": result.expires_at,
                "file_size": result.file_size,
                "message": "落地页已导出",
            }

        except MCPError as e:
            logger.error(
                "export_landing_page_mcp_error",
                error=str(e),
                error_code=e.code,
            )
            return {
                "status": "error",
                "error": {
                    "code": e.code or "EXPORT_FAILED",
                    "type": "EXPORT_ERROR",
                    "message": e.message or f"Failed to export landing page: {str(e)}",
                    "retry_allowed": True,
                },
            }

        except Exception as e:
            logger.error(
                "export_landing_page_failed",
                error=str(e),
                exc_info=True,
            )
            return {
                "status": "error",
                "error": {
                    "code": "EXPORT_FAILED",
                    "type": "EXPORT_ERROR",
                    "message": f"Failed to export landing page: {str(e)}",
                    "retry_allowed": True,
                },
            }
