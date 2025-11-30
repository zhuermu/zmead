"""
Strategy generator for Market Insights module.

Uses AI to generate comprehensive ad strategies including audience recommendations,
creative direction, budget planning, and campaign structure.

Requirements: 4.1, 4.2, 4.3, 4.4, 4.5
"""

from typing import TYPE_CHECKING, Literal

import structlog
from pydantic import BaseModel, Field

from ..models import (
    AdGroup,
    AdStrategy,
    AdStrategyResponse,
    AudienceRecommendation,
    BudgetPlanning,
    CampaignStructure,
    CreativeDirection,
    ProductInfo,
)

if TYPE_CHECKING:
    from app.services.gemini_client import GeminiClient
    from app.services.mcp_client import MCPClient

logger = structlog.get_logger(__name__)


class AudienceRecommendationAI(BaseModel):
    """AI output schema for audience recommendation."""

    age_range: str = Field(description="目标年龄范围（如 25-45）")
    gender: Literal["all", "male", "female"] = Field(description="目标性别")
    interests: list[str] = Field(description="兴趣标签列表")
    behaviors: list[str] = Field(description="行为标签列表")


class CreativeDirectionAI(BaseModel):
    """AI output schema for creative direction."""

    visual_style: str = Field(description="视觉风格建议")
    key_messages: list[str] = Field(description="关键信息列表")
    content_types: list[str] = Field(description="内容类型列表（如产品演示、使用场景等）")
    color_recommendations: list[str] = Field(description="色彩推荐列表")


class BudgetPlanningAI(BaseModel):
    """AI output schema for budget planning."""

    recommended_daily_budget: float = Field(description="建议每日预算（美元）")
    campaign_duration: str = Field(description="建议投放周期（如 30 days）")
    expected_reach: str = Field(description="预期触达人数范围（如 50,000-100,000）")


class AdGroupAI(BaseModel):
    """AI output schema for ad group."""

    name: str = Field(description="广告组名称")
    targeting: str = Field(description="定向策略描述")
    budget_allocation: str = Field(description="预算分配百分比（如 40%）")


class AdStrategyAIResult(BaseModel):
    """Structured output schema for Gemini ad strategy generation."""

    audience_recommendations: AudienceRecommendationAI = Field(
        description="受众推荐"
    )
    creative_direction: CreativeDirectionAI = Field(description="素材方向建议")
    budget_planning: BudgetPlanningAI = Field(description="预算规划")
    ad_groups: list[AdGroupAI] = Field(description="广告组列表")
    rationale: str = Field(description="策略依据说明")



class StrategyGeneratorError(Exception):
    """Error raised during strategy generation."""

    def __init__(
        self,
        message: str,
        code: str | None = None,
        retryable: bool = False,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.retryable = retryable


class StrategyGenerator:
    """Generates AI-powered ad strategies.

    Creates comprehensive advertising strategies including:
    - Audience recommendations: demographics, interests, behaviors
    - Creative direction: visual style, messaging, content types
    - Budget planning: daily budget, duration, expected reach
    - Campaign structure: ad groups with targeting and budget allocation

    Uses Gemini 2.5 Pro for comprehensive AI strategy generation.

    Requirements: 4.1, 4.2, 4.3, 4.4, 4.5
    """

    STRATEGY_PROMPT = """你是一位专业的广告策略师。请基于以下产品信息生成完整的广告投放策略。

**产品信息：**
- 产品名称：{product_name}
- 产品类别：{product_category}
- 产品价格：${product_price}
- 目标市场：{target_market}

{competitor_section}

{trend_section}

**请生成以下策略内容：**

1. **受众推荐 (Audience Recommendations)**
   - 目标年龄范围（如 25-45）
   - 目标性别（all/male/female）
   - 兴趣标签（3-5个相关兴趣）
   - 行为标签（3-5个相关行为）

2. **素材方向 (Creative Direction)**
   - 视觉风格建议
   - 关键信息（3-5条核心卖点信息）
   - 内容类型（如产品演示、使用场景、用户评价等）
   - 色彩推荐（3-5个推荐颜色）

3. **预算规划 (Budget Planning)**
   - 建议每日预算（美元）
   - 建议投放周期
   - 预期触达人数范围

4. **广告系列结构 (Campaign Structure)**
   - 设计 2-4 个广告组
   - 每个广告组包含：名称、定向策略、预算分配百分比
   - 预算分配总和应为 100%

5. **策略依据 (Rationale)**
   - 解释策略制定的依据和逻辑
   - 说明为什么这个策略适合该产品

请用中文回答，策略要具体、可执行、有数据支撑。"""

    COMPETITOR_SECTION_TEMPLATE = """
**竞品分析结果：**
{competitor_analysis}
"""

    TREND_SECTION_TEMPLATE = """
**市场趋势分析：**
{trend_analysis}
"""

    def __init__(
        self,
        gemini_client: "GeminiClient | None" = None,
        mcp_client: "MCPClient | None" = None,
    ):
        """Initialize strategy generator.

        Args:
            gemini_client: Gemini client for AI generation
            mcp_client: MCP client for data storage
        """
        self.gemini = gemini_client
        self.mcp = mcp_client
        self._log = logger.bind(component="strategy_generator")

    def _get_gemini_client(self) -> "GeminiClient":
        """Get or create Gemini client.

        Returns:
            GeminiClient instance
        """
        if self.gemini is not None:
            return self.gemini

        from app.services.gemini_client import GeminiClient

        self.gemini = GeminiClient()
        return self.gemini

    def _get_mcp_client(self) -> "MCPClient":
        """Get or create MCP client.

        Returns:
            MCPClient instance
        """
        if self.mcp is not None:
            return self.mcp

        from app.services.mcp_client import MCPClient

        self.mcp = MCPClient()
        return self.mcp

    async def generate_audience_recommendations(
        self,
        product_info: ProductInfo,
        trends: dict | None = None,
    ) -> AudienceRecommendation:
        """Generate audience recommendations based on product and trends.

        Args:
            product_info: Product information
            trends: Optional market trends data

        Returns:
            AudienceRecommendation with targeting suggestions

        Requirements: 4.2
        """
        log = self._log.bind(product_name=product_info.name)
        log.info("generate_audience_recommendations_start")

        # This is called as part of the full strategy generation
        # For standalone use, we generate a simplified strategy
        strategy = await self.generate(product_info, trend_analysis=trends)

        if strategy.status == "success" and strategy.strategy:
            return strategy.strategy.audience_recommendations

        # Return default if generation failed
        return AudienceRecommendation(
            age_range="25-45",
            gender="all",
            interests=["general"],
            behaviors=["online shoppers"],
        )

    async def generate_creative_direction(
        self,
        product_info: ProductInfo,
        competitor_analysis: dict | None = None,
    ) -> CreativeDirection:
        """Generate creative direction based on product and competitor analysis.

        Args:
            product_info: Product information
            competitor_analysis: Optional competitor analysis data

        Returns:
            CreativeDirection with creative suggestions

        Requirements: 4.3
        """
        log = self._log.bind(product_name=product_info.name)
        log.info("generate_creative_direction_start")

        # This is called as part of the full strategy generation
        strategy = await self.generate(product_info, competitor_analysis=competitor_analysis)

        if strategy.status == "success" and strategy.strategy:
            return strategy.strategy.creative_direction

        # Return default if generation failed
        return CreativeDirection(
            visual_style="现代简约",
            key_messages=["高品质", "物超所值"],
            content_types=["产品展示"],
            color_recommendations=["蓝色", "白色"],
        )


    async def generate(
        self,
        product_info: ProductInfo,
        competitor_analysis: dict | None = None,
        trend_analysis: dict | None = None,
    ) -> AdStrategyResponse:
        """Generate comprehensive ad strategy.

        Uses AI to generate a complete advertising strategy including
        audience recommendations, creative direction, budget planning,
        and campaign structure.

        Args:
            product_info: Product information
            competitor_analysis: Optional competitor analysis data
            trend_analysis: Optional market trends data

        Returns:
            AdStrategyResponse with complete strategy

        Requirements: 4.1, 4.2, 4.3, 4.4, 4.5
        """
        log = self._log.bind(
            product_name=product_info.name,
            product_category=product_info.category,
            has_competitor_analysis=competitor_analysis is not None,
            has_trend_analysis=trend_analysis is not None,
        )
        log.info("generate_strategy_start")

        try:
            # Build prompt sections
            competitor_section = ""
            if competitor_analysis:
                competitor_section = self.COMPETITOR_SECTION_TEMPLATE.format(
                    competitor_analysis=self._format_competitor_analysis(competitor_analysis)
                )

            trend_section = ""
            if trend_analysis:
                trend_section = self.TREND_SECTION_TEMPLATE.format(
                    trend_analysis=self._format_trend_analysis(trend_analysis)
                )

            # Build full prompt
            prompt = self.STRATEGY_PROMPT.format(
                product_name=product_info.name,
                product_category=product_info.category,
                product_price=product_info.price,
                target_market=product_info.target_market,
                competitor_section=competitor_section,
                trend_section=trend_section,
            )

            # Generate strategy using AI
            ai_result = await self._generate_with_ai(prompt)

            # Convert AI result to response models
            strategy = self._convert_ai_result(ai_result)

            response = AdStrategyResponse(
                status="success",
                strategy=strategy,
                rationale=ai_result.rationale,
            )

            log.info(
                "generate_strategy_complete",
                ad_groups_count=len(ai_result.ad_groups),
            )

            return response

        except StrategyGeneratorError as e:
            log.error("generate_strategy_failed", error=str(e), code=e.code)
            return AdStrategyResponse(
                status="error",
                strategy=None,
                rationale="",
                error_code=e.code or "GENERATION_ERROR",
                message=e.message,
            )

        except Exception as e:
            log.error("generate_strategy_unexpected_error", error=str(e))
            return AdStrategyResponse(
                status="error",
                strategy=None,
                rationale="",
                error_code="UNEXPECTED_ERROR",
                message=f"Unexpected error during strategy generation: {e}",
            )

    async def _generate_with_ai(self, prompt: str) -> AdStrategyAIResult:
        """Generate strategy using AI.

        Args:
            prompt: Full prompt for AI

        Returns:
            AI-generated strategy result

        Raises:
            StrategyGeneratorError: If AI generation fails
        """
        log = self._log
        log.info("generate_with_ai_start")

        gemini = self._get_gemini_client()

        messages = [
            {
                "role": "user",
                "content": prompt,
            }
        ]

        try:
            # Use Pro model for comprehensive strategy generation
            result: AdStrategyAIResult = await gemini.structured_output(
                messages=messages,
                schema=AdStrategyAIResult,
                temperature=0.3,
            )

            log.info(
                "generate_with_ai_success",
                ad_groups_count=len(result.ad_groups),
            )

            return result

        except Exception as e:
            log.error("generate_with_ai_failed", error=str(e))
            raise StrategyGeneratorError(
                f"AI strategy generation failed: {e}",
                code="AI_ERROR",
                retryable=True,
            )

    def _convert_ai_result(self, ai_result: AdStrategyAIResult) -> AdStrategy:
        """Convert AI result to AdStrategy model.

        Args:
            ai_result: AI-generated result

        Returns:
            AdStrategy model
        """
        audience = AudienceRecommendation(
            age_range=ai_result.audience_recommendations.age_range,
            gender=ai_result.audience_recommendations.gender,
            interests=ai_result.audience_recommendations.interests,
            behaviors=ai_result.audience_recommendations.behaviors,
        )

        creative = CreativeDirection(
            visual_style=ai_result.creative_direction.visual_style,
            key_messages=ai_result.creative_direction.key_messages,
            content_types=ai_result.creative_direction.content_types,
            color_recommendations=ai_result.creative_direction.color_recommendations,
        )

        budget = BudgetPlanning(
            recommended_daily_budget=ai_result.budget_planning.recommended_daily_budget,
            campaign_duration=ai_result.budget_planning.campaign_duration,
            expected_reach=ai_result.budget_planning.expected_reach,
        )

        ad_groups = [
            AdGroup(
                name=ag.name,
                targeting=ag.targeting,
                budget_allocation=ag.budget_allocation,
            )
            for ag in ai_result.ad_groups
        ]

        campaign_structure = CampaignStructure(ad_groups=ad_groups)

        return AdStrategy(
            audience_recommendations=audience,
            creative_direction=creative,
            budget_planning=budget,
            campaign_structure=campaign_structure,
        )

    def _format_competitor_analysis(self, analysis: dict) -> str:
        """Format competitor analysis for prompt.

        Args:
            analysis: Competitor analysis data

        Returns:
            Formatted string
        """
        parts = []

        if "competitor_info" in analysis:
            info = analysis["competitor_info"]
            parts.append(f"- 竞品名称: {info.get('name', 'N/A')}")
            parts.append(f"- 竞品价格: {info.get('price', 'N/A')}")
            if info.get("selling_points"):
                parts.append(f"- 竞品卖点: {', '.join(info['selling_points'])}")

        if "insights" in analysis:
            insights = analysis["insights"]
            if insights.get("strengths"):
                parts.append(f"- 竞品优势: {', '.join(insights['strengths'])}")
            if insights.get("weaknesses"):
                parts.append(f"- 竞品劣势: {', '.join(insights['weaknesses'])}")

        return "\n".join(parts) if parts else "无竞品分析数据"

    def _format_trend_analysis(self, analysis: dict) -> str:
        """Format trend analysis for prompt.

        Args:
            analysis: Trend analysis data

        Returns:
            Formatted string
        """
        parts = []

        if "trends" in analysis:
            for trend in analysis["trends"][:5]:  # Top 5 trends
                keyword = trend.get("keyword", "N/A")
                direction = trend.get("trend_direction", "N/A")
                growth = trend.get("growth_rate", 0)
                parts.append(f"- {keyword}: {direction} ({growth:+.1f}%)")

        if "insights" in analysis:
            insights = analysis["insights"]
            if insights.get("hot_topics"):
                parts.append(f"- 热门话题: {', '.join(insights['hot_topics'])}")
            if insights.get("emerging_trends"):
                parts.append(f"- 新兴趋势: {', '.join(insights['emerging_trends'])}")

        return "\n".join(parts) if parts else "无市场趋势数据"

    async def save_strategy(
        self,
        user_id: str,
        product_info: ProductInfo,
        response: AdStrategyResponse,
    ) -> dict:
        """Save strategy to Web Platform via MCP.

        Args:
            user_id: User ID
            product_info: Product information
            response: Strategy response to save

        Returns:
            Save result from MCP
        """
        log = self._log.bind(user_id=user_id, product_name=product_info.name)
        log.info("save_strategy_start")

        if response.status != "success" or response.strategy is None:
            log.warning("save_strategy_skipped_error_result")
            return {"saved": False, "reason": "Strategy generation was not successful"}

        mcp = self._get_mcp_client()

        try:
            result = await mcp.call_tool(
                "save_insight",
                {
                    "user_id": user_id,
                    "insight_type": "ad_strategy",
                    "data": {
                        "product_info": product_info.model_dump(),
                        "strategy": response.strategy.model_dump(),
                        "rationale": response.rationale,
                    },
                },
            )

            log.info("save_strategy_complete")
            return result

        except Exception as e:
            log.error("save_strategy_failed", error=str(e))
            raise
