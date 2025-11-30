"""
Market Insights capability - Main entry point for the module.

This module provides the main entry point for Market Insights functionality,
including competitor analysis, trending creatives, market trends, ad strategy
generation, and strategy performance tracking.

Requirements: 1.1-1.5, 2.1-2.5, 3.1-3.5, 4.1-4.5, 5.1-5.5, 6.1-6.6, 7.1-7.5
"""

import asyncio
import os

import structlog
from redis.asyncio import Redis

from app.core.errors import ErrorHandler
from app.services.gemini_client import GeminiClient, GeminiError
from app.services.mcp_client import MCPClient, MCPError

from .analyzers import CompetitorAnalyzer, CreativeAnalyzer, StrategyGenerator
from .fetchers import TikTokFetcher, TrendsFetcher
from .trackers import PerformanceTracker
from .utils.cache_manager import CacheManager
from .utils.degradation_handler import DegradationHandler
from .utils.error_handler import MarketInsightsErrorHandler
from .models import (
    CompetitorAnalysis,
    TrendingCreativesResponse,
    CreativeAnalysisResponse,
    MarketTrendsResponse,
    AdStrategyResponse,
    StrategyPerformanceResponse,
    ProductInfo,
)

logger = structlog.get_logger(__name__)


class MarketInsights:
    """Market Insights 功能模块主入口

    Provides comprehensive market intelligence including:
    - Competitor analysis with AI-powered insights
    - Trending creatives from TikTok Creative Center
    - Market trends from Google Trends (pytrends)
    - AI-generated ad strategies
    - Strategy performance tracking

    Requirements: 1.1-1.5, 2.1-2.5, 3.1-3.5, 4.1-4.5, 5.1-5.5, 6.1-6.6, 7.1-7.5
    """

    def __init__(
        self,
        mcp_client: MCPClient | None = None,
        gemini_client: GeminiClient | None = None,
        redis_client: Redis | None = None,
    ):
        """初始化 Market Insights 模块

        Args:
            mcp_client: MCP client for Web Platform communication
            gemini_client: Gemini client for AI analysis
            redis_client: Redis client for caching
        """
        self.mcp_client = mcp_client or MCPClient()
        self.gemini_client = gemini_client or GeminiClient()
        self.redis_client = redis_client

        # Initialize cache manager if Redis is available
        self.cache_manager: CacheManager | None = None
        if self.redis_client:
            self.cache_manager = CacheManager(self.redis_client)

        # Initialize degradation handler
        self.degradation_handler: DegradationHandler | None = None
        if self.cache_manager:
            self.degradation_handler = DegradationHandler(
                cache_manager=self.cache_manager,
                gemini_client=self.gemini_client,
            )

        # Initialize fetchers
        self.tiktok_fetcher: TikTokFetcher | None = None
        self.trends_fetcher: TrendsFetcher | None = None
        self._init_fetchers()

        logger.info(
            "market_insights_initialized",
            has_mcp=self.mcp_client is not None,
            has_gemini=self.gemini_client is not None,
            has_redis=self.redis_client is not None,
            has_cache=self.cache_manager is not None,
            has_tiktok_fetcher=self.tiktok_fetcher is not None,
            has_trends_fetcher=self.trends_fetcher is not None,
        )

    def _init_fetchers(self) -> None:
        """Initialize data fetchers with API credentials."""
        # Initialize TikTok fetcher if credentials are available
        tiktok_api_key = os.getenv("TIKTOK_API_KEY")
        tiktok_api_secret = os.getenv("TIKTOK_API_SECRET")
        if tiktok_api_key and tiktok_api_secret:
            self.tiktok_fetcher = TikTokFetcher(
                api_key=tiktok_api_key,
                api_secret=tiktok_api_secret,
                cache_manager=self.cache_manager,
            )

        # Initialize trends fetcher (no credentials needed for pytrends)
        self.trends_fetcher = TrendsFetcher(cache_manager=self.cache_manager)

    async def execute(self, action: str, parameters: dict, context: dict) -> dict:
        """
        执行市场洞察操作

        Implements action routing with comprehensive error handling and logging.
        All errors are caught and converted to structured error responses.

        Args:
            action: 操作名称 (analyze_competitor, get_trending_creatives, etc.)
            parameters: 操作参数
            context: 上下文信息（user_id, session_id等）

        Returns:
            操作结果，格式：
            - 成功: {"status": "success", "data": {...}, "message": "..."}
            - 失败: {"status": "error", "error": {...}}

        Requirements: All
        """
        user_id = context.get("user_id")
        session_id = context.get("session_id")

        log = logger.bind(
            action=action,
            user_id=user_id,
            session_id=session_id,
        )

        log.info("market_insights_execute_start", parameters=parameters)

        try:
            # Route to appropriate handler
            if action == "analyze_competitor":
                result = await self._analyze_competitor(parameters, context)
            elif action == "get_trending_creatives":
                result = await self._get_trending_creatives(parameters, context)
            elif action == "analyze_creative_trend":
                result = await self._analyze_creative_trend(parameters, context)
            elif action == "get_market_trends":
                result = await self._get_market_trends(parameters, context)
            elif action == "generate_ad_strategy":
                result = await self._generate_ad_strategy(parameters, context)
            elif action == "track_strategy_performance":
                result = await self._track_strategy_performance(parameters, context)
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
                            "supported_actions": [
                                "analyze_competitor",
                                "get_trending_creatives",
                                "analyze_creative_trend",
                                "get_market_trends",
                                "generate_ad_strategy",
                                "track_strategy_performance",
                            ],
                        },
                    },
                }

            log.info("market_insights_execute_success", action=action)
            return result

        except (MCPError, GeminiError) as e:
            # Handle known service errors
            log.error(
                "market_insights_service_error",
                error=str(e),
                error_type=type(e).__name__,
            )
            return MarketInsightsErrorHandler.create_error_response(
                error=e,
                context=f"market_insights.{action}",
            )

        except Exception as e:
            # Handle unexpected errors
            log.error(
                "market_insights_unexpected_error",
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )
            return MarketInsightsErrorHandler.create_error_response(
                error=e,
                context=f"market_insights.{action}",
            )

    async def _analyze_competitor(self, parameters: dict, context: dict) -> dict:
        """分析竞品

        Uses AI to analyze competitor product information, pricing strategy,
        target audience, and generate competitive insights.

        Args:
            parameters: {
                "competitor_url": str,
                "analysis_type": "product" (default),
                "depth": "detailed" (default)
            }
            context: {"user_id": str, "session_id": str}

        Returns:
            CompetitorAnalysis response dict

        Requirements: 1.1, 1.2, 1.3, 1.4, 1.5
        """
        user_id = context.get("user_id")
        competitor_url = parameters.get("competitor_url")
        analysis_type = parameters.get("analysis_type", "product")
        depth = parameters.get("depth", "detailed")

        log = logger.bind(
            user_id=user_id,
            competitor_url=competitor_url,
            analysis_type=analysis_type,
            depth=depth,
        )
        log.info("analyze_competitor_start")

        # Use CompetitorAnalyzer for analysis
        analyzer = CompetitorAnalyzer(
            gemini_client=self.gemini_client,
            mcp_client=self.mcp_client,
        )

        try:
            result = await analyzer.analyze(
                competitor_url=competitor_url,
                analysis_type=analysis_type,
                depth=depth,
            )

            # Save analysis if successful
            if result.status == "success" and user_id:
                try:
                    await self._save_insight(
                        user_id=user_id,
                        insight_type="competitor_analysis",
                        data={
                            "competitor_url": competitor_url,
                            "analysis_type": analysis_type,
                            "result": result.model_dump(),
                        },
                    )
                except Exception as e:
                    log.warning("save_analysis_failed", error=str(e))

            return result.model_dump()

        finally:
            await analyzer.close()

    async def _get_trending_creatives(self, parameters: dict, context: dict) -> dict:
        """获取热门素材

        Fetches trending creatives from TikTok Creative Center API.

        Args:
            parameters: {
                "industry": str,
                "region": str,
                "time_range": "7d" (default),
                "limit": 20 (default)
            }
            context: {"user_id": str, "session_id": str}

        Returns:
            TrendingCreativesResponse dict

        Requirements: 2.1, 2.2, 2.3
        """
        user_id = context.get("user_id")
        industry = parameters.get("industry")
        region = parameters.get("region")
        time_range = parameters.get("time_range", "7d")
        limit = parameters.get("limit", 20)

        log = logger.bind(
            user_id=user_id,
            industry=industry,
            region=region,
            time_range=time_range,
            limit=limit,
        )
        log.info("get_trending_creatives_start")

        # Check if TikTok fetcher is available
        if not self.tiktok_fetcher:
            log.warning("tiktok_fetcher_not_available")
            # Try degradation handler
            if self.degradation_handler:
                cache_key = f"{industry}:{region}:{time_range}:{limit}"
                degraded_result = await self.degradation_handler.handle_tiktok_unavailable(
                    cache_key=cache_key,
                    industry=industry,
                    region=region,
                )
                if degraded_result.get("status") == "success":
                    return degraded_result.get("data", {})
                return TrendingCreativesResponse(
                    status="error",
                    creatives=[],
                    total=0,
                    message="TikTok API credentials not configured",
                ).model_dump()

            return TrendingCreativesResponse(
                status="error",
                creatives=[],
                total=0,
                message="TikTok API credentials not configured",
            ).model_dump()

        # Fetch trending creatives
        result = await self.tiktok_fetcher.get_trending_creatives(
            industry=industry,
            region=region,
            time_range=time_range,
            limit=limit,
        )

        return result.model_dump()

    async def _analyze_creative_trend(self, parameters: dict, context: dict) -> dict:
        """分析素材趋势

        Uses AI Vision to analyze creative visual style, elements, and success factors.

        Args:
            parameters: {
                "creative_id": str,
                "analysis_depth": "detailed" (default)
            }
            context: {"user_id": str, "session_id": str}

        Returns:
            CreativeAnalysisResponse dict

        Requirements: 2.4, 2.5
        """
        user_id = context.get("user_id")
        creative_id = parameters.get("creative_id")
        analysis_depth = parameters.get("analysis_depth", "detailed")

        log = logger.bind(
            user_id=user_id,
            creative_id=creative_id,
            analysis_depth=analysis_depth,
        )
        log.info("analyze_creative_trend_start")

        # Use CreativeAnalyzer for analysis
        analyzer = CreativeAnalyzer(
            gemini_client=self.gemini_client,
            mcp_client=self.mcp_client,
        )

        try:
            result = await analyzer.analyze_creative(
                creative_id=creative_id,
                analysis_depth=analysis_depth,
            )

            # Save analysis if successful
            if result.status == "success" and user_id:
                try:
                    await self._save_insight(
                        user_id=user_id,
                        insight_type="creative_analysis",
                        data={
                            "creative_id": creative_id,
                            "result": result.model_dump(),
                        },
                    )
                except Exception as e:
                    log.warning("save_analysis_failed", error=str(e))

            return result.model_dump()

        finally:
            await analyzer.close()

    async def _get_market_trends(self, parameters: dict, context: dict) -> dict:
        """获取市场趋势

        Fetches market trends from Google Trends using pytrends.

        Args:
            parameters: {
                "keywords": list[str],
                "region": str,
                "time_range": "30d" (default)
            }
            context: {"user_id": str, "session_id": str}

        Returns:
            MarketTrendsResponse dict

        Requirements: 3.1, 3.2, 3.3, 3.4, 3.5
        """
        user_id = context.get("user_id")
        keywords = parameters.get("keywords", [])
        region = parameters.get("region")
        time_range = parameters.get("time_range", "30d")

        log = logger.bind(
            user_id=user_id,
            keywords=keywords,
            region=region,
            time_range=time_range,
        )
        log.info("get_market_trends_start")

        # Check if trends fetcher is available
        if not self.trends_fetcher:
            log.warning("trends_fetcher_not_available")
            return MarketTrendsResponse(
                status="error",
                trends=[],
                insights=None,
                message="Trends fetcher not initialized",
            ).model_dump()

        # Fetch market trends
        result = await self.trends_fetcher.get_interest_over_time(
            keywords=keywords,
            region=region,
            time_range=time_range,
        )

        return result.model_dump()

    async def _generate_ad_strategy(self, parameters: dict, context: dict) -> dict:
        """生成广告策略

        Uses AI to generate comprehensive ad strategy including audience
        recommendations, creative direction, budget planning, and campaign structure.
        Optionally includes competitor and trend analysis for better recommendations.

        Args:
            parameters: {
                "product_info": {
                    "name": str,
                    "category": str,
                    "price": float,
                    "target_market": str
                },
                "competitor_analysis": bool (default True),
                "trend_analysis": bool (default True),
                "competitor_url": str (optional)
            }
            context: {"user_id": str, "session_id": str}

        Returns:
            AdStrategyResponse dict

        Requirements: 4.1, 4.2, 4.3, 4.4, 4.5
        """
        user_id = context.get("user_id")
        product_info_dict = parameters.get("product_info", {})
        include_competitor_analysis = parameters.get("competitor_analysis", True)
        include_trend_analysis = parameters.get("trend_analysis", True)
        competitor_url = parameters.get("competitor_url")

        log = logger.bind(
            user_id=user_id,
            product_name=product_info_dict.get("name"),
            competitor_analysis=include_competitor_analysis,
            trend_analysis=include_trend_analysis,
        )
        log.info("generate_ad_strategy_start")

        # Convert dict to ProductInfo model
        try:
            product_info = ProductInfo(
                name=product_info_dict.get("name", "Unknown Product"),
                category=product_info_dict.get("category", "general"),
                price=float(product_info_dict.get("price", 0)),
                target_market=product_info_dict.get("target_market", "US"),
            )
        except Exception as e:
            log.error("invalid_product_info", error=str(e))
            return AdStrategyResponse(
                status="error",
                strategy=None,
                rationale="",
                error_code="INVALID_PARAMS",
                message=f"Invalid product info: {e}",
            ).model_dump()

        # Fetch additional data in parallel if requested
        competitor_data = None
        trend_data = None

        tasks = []
        if include_competitor_analysis and competitor_url:
            tasks.append(self._fetch_competitor_data_for_strategy(competitor_url))
        else:
            tasks.append(asyncio.sleep(0))  # Placeholder

        if include_trend_analysis:
            # Use product category as keyword for trend analysis
            keywords = [product_info.category, product_info.name.split()[0]]
            tasks.append(
                self._fetch_trend_data_for_strategy(
                    keywords=keywords,
                    region=product_info.target_market,
                )
            )
        else:
            tasks.append(asyncio.sleep(0))  # Placeholder

        # Execute parallel fetches
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        if include_competitor_analysis and competitor_url:
            if not isinstance(results[0], Exception) and results[0]:
                competitor_data = results[0]
            else:
                log.warning("competitor_data_fetch_failed", error=str(results[0]))

        if include_trend_analysis:
            if not isinstance(results[1], Exception) and results[1]:
                trend_data = results[1]
            else:
                log.warning("trend_data_fetch_failed", error=str(results[1]))

        # Use StrategyGenerator for strategy generation
        generator = StrategyGenerator(
            gemini_client=self.gemini_client,
            mcp_client=self.mcp_client,
        )

        result = await generator.generate(
            product_info=product_info,
            competitor_analysis=competitor_data,
            trend_analysis=trend_data,
        )

        # Save strategy if successful
        if result.status == "success" and user_id:
            try:
                await self._save_insight(
                    user_id=user_id,
                    insight_type="ad_strategy",
                    data={
                        "product_info": product_info.model_dump(),
                        "result": result.model_dump(),
                    },
                )
            except Exception as e:
                log.warning("save_strategy_failed", error=str(e))

        return result.model_dump()

    async def _fetch_competitor_data_for_strategy(
        self, competitor_url: str
    ) -> dict | None:
        """Fetch competitor data for strategy generation.

        Args:
            competitor_url: URL of competitor to analyze

        Returns:
            Competitor analysis data or None if failed
        """
        try:
            analyzer = CompetitorAnalyzer(
                gemini_client=self.gemini_client,
                mcp_client=self.mcp_client,
            )
            try:
                result = await analyzer.analyze(
                    competitor_url=competitor_url,
                    analysis_type="product",
                    depth="basic",
                )
                if result.status == "success":
                    return result.model_dump()
            finally:
                await analyzer.close()
        except Exception as e:
            logger.warning("competitor_fetch_for_strategy_failed", error=str(e))
        return None

    async def _fetch_trend_data_for_strategy(
        self, keywords: list[str], region: str
    ) -> dict | None:
        """Fetch trend data for strategy generation.

        Args:
            keywords: Keywords to analyze
            region: Target region

        Returns:
            Trend data or None if failed
        """
        if not self.trends_fetcher:
            return None

        try:
            result = await self.trends_fetcher.get_interest_over_time(
                keywords=keywords,
                region=region,
                time_range="30d",
            )
            if result.status == "success":
                return result.model_dump()
        except Exception as e:
            logger.warning("trend_fetch_for_strategy_failed", error=str(e))
        return None

    async def _track_strategy_performance(
        self, parameters: dict, context: dict
    ) -> dict:
        """追踪策略效果

        Compares performance of campaigns with and without AI strategy.

        Args:
            parameters: {
                "strategy_id": str,
                "campaign_ids": list[str],
                "comparison_period": "7d" (default)
            }
            context: {"user_id": str, "session_id": str}

        Returns:
            StrategyPerformanceResponse dict

        Requirements: 5.1, 5.2, 5.3, 5.4, 5.5
        """
        user_id = context.get("user_id")
        strategy_id = parameters.get("strategy_id")
        campaign_ids = parameters.get("campaign_ids", [])
        comparison_period = parameters.get("comparison_period", "7d")

        log = logger.bind(
            user_id=user_id,
            strategy_id=strategy_id,
            campaign_count=len(campaign_ids),
            comparison_period=comparison_period,
        )
        log.info("track_strategy_performance_start")

        # Use PerformanceTracker for tracking
        tracker = PerformanceTracker(mcp_client=self.mcp_client)

        try:
            result = await tracker.track(
                strategy_id=strategy_id,
                campaign_ids=campaign_ids,
                comparison_period=comparison_period,
            )

            return result.model_dump()

        finally:
            await tracker.close()

    async def _save_insight(
        self, user_id: str, insight_type: str, data: dict
    ) -> dict | None:
        """Save insight to Web Platform via MCP.

        Args:
            user_id: User ID
            insight_type: Type of insight (competitor_analysis, ad_strategy, etc.)
            data: Insight data to save

        Returns:
            MCP response or None if failed
        """
        try:
            result = await self.mcp_client.call_tool(
                "save_insight",
                {
                    "user_id": user_id,
                    "insight_type": insight_type,
                    "data": data,
                },
            )
            logger.info(
                "insight_saved",
                user_id=user_id,
                insight_type=insight_type,
            )
            return result
        except Exception as e:
            logger.warning(
                "save_insight_failed",
                user_id=user_id,
                insight_type=insight_type,
                error=str(e),
            )
            return None

    async def _get_insights(
        self, user_id: str, insight_type: str, limit: int = 10
    ) -> list[dict]:
        """Get historical insights from Web Platform via MCP.

        Args:
            user_id: User ID
            insight_type: Type of insight to retrieve
            limit: Maximum number of insights to return

        Returns:
            List of insight dicts
        """
        try:
            result = await self.mcp_client.call_tool(
                "get_insights",
                {
                    "user_id": user_id,
                    "insight_type": insight_type,
                    "limit": limit,
                },
            )
            return result.get("insights", [])
        except Exception as e:
            logger.warning(
                "get_insights_failed",
                user_id=user_id,
                insight_type=insight_type,
                error=str(e),
            )
            return []

    async def get_comprehensive_insights(
        self,
        product_info: dict,
        competitor_url: str | None = None,
        context: dict | None = None,
    ) -> dict:
        """Get comprehensive market insights in parallel.

        Fetches multiple types of insights simultaneously for efficiency.

        Args:
            product_info: Product information dict
            competitor_url: Optional competitor URL to analyze
            context: Optional context with user_id, session_id

        Returns:
            Dict with trends, creatives, and competitor data
        """
        context = context or {}
        category = product_info.get("category", "general")
        target_market = product_info.get("target_market", "US")

        tasks = []

        # Fetch market trends
        tasks.append(
            self._get_market_trends(
                parameters={
                    "keywords": [category, product_info.get("name", "").split()[0]],
                    "region": target_market,
                    "time_range": "30d",
                },
                context=context,
            )
        )

        # Fetch trending creatives
        tasks.append(
            self._get_trending_creatives(
                parameters={
                    "industry": category,
                    "region": target_market,
                    "time_range": "7d",
                    "limit": 10,
                },
                context=context,
            )
        )

        # Fetch competitor analysis if URL provided
        if competitor_url:
            tasks.append(
                self._analyze_competitor(
                    parameters={
                        "competitor_url": competitor_url,
                        "analysis_type": "product",
                        "depth": "detailed",
                    },
                    context=context,
                )
            )

        # Execute all tasks in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Build response
        response = {
            "trends": None,
            "creatives": None,
            "competitor": None,
        }

        # Process trends result
        if not isinstance(results[0], Exception):
            response["trends"] = results[0]
        else:
            logger.warning("trends_fetch_failed", error=str(results[0]))

        # Process creatives result
        if not isinstance(results[1], Exception):
            response["creatives"] = results[1]
        else:
            logger.warning("creatives_fetch_failed", error=str(results[1]))

        # Process competitor result if available
        if competitor_url and len(results) > 2:
            if not isinstance(results[2], Exception):
                response["competitor"] = results[2]
            else:
                logger.warning("competitor_fetch_failed", error=str(results[2]))

        return response
