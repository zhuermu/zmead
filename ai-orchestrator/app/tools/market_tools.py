"""Market Tools for market insights and competitor analysis.

This module provides Agent Custom Tools for market intelligence operations:
- analyze_competitor_tool: Analyze competitor strategies using Gemini
- analyze_trends_tool: Analyze market trends using Gemini
- generate_strategy_tool: Generate marketing strategies using Gemini

These tools can call LLMs (Gemini) for AI capabilities.
They call the module functions directly (not through capability.py).
"""

import structlog
from typing import Any

from app.services.gemini_client import GeminiClient, GeminiError
from app.tools.base import (
    AgentTool,
    ToolCategory,
    ToolExecutionError,
    ToolMetadata,
    ToolParameter,
)

logger = structlog.get_logger(__name__)


class AnalyzeCompetitorTool(AgentTool):
    """Tool for analyzing competitor strategies using Gemini.

    This tool analyzes competitor information and provides insights
    on their strategies, strengths, weaknesses, and opportunities.
    """

    def __init__(self, gemini_client: GeminiClient | None = None):
        """Initialize the analyze competitor tool.

        Args:
            gemini_client: Gemini client for analysis
        """
        metadata = ToolMetadata(
            name="analyze_competitor_tool",
            description=(
                "Analyze competitor strategies and positioning using AI. "
                "Provides insights on competitor strengths, weaknesses, "
                "messaging, and opportunities for differentiation."
            ),
            category=ToolCategory.AGENT_CUSTOM,
            parameters=[
                ToolParameter(
                    name="competitor_url",
                    type="string",
                    description="Competitor website or product URL",
                    required=False,
                ),
                ToolParameter(
                    name="competitor_info",
                    type="object",
                    description="Competitor information (name, products, messaging)",
                    required=False,
                ),
                ToolParameter(
                    name="analysis_focus",
                    type="array",
                    description="Specific areas to focus analysis on",
                    required=False,
                    default=["messaging", "pricing", "features"],
                ),
            ],
            returns="object with competitor analysis insights",
            credit_cost=3.0,
            tags=["market", "competitor", "analysis", "ai"],
        )

        super().__init__(metadata)

        self.gemini_client = gemini_client or GeminiClient()

    async def execute(
        self,
        parameters: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute competitor analysis.

        Args:
            parameters: Tool parameters
            context: Execution context

        Returns:
            Competitor analysis insights

        Raises:
            ToolExecutionError: If analysis fails
        """
        competitor_url = parameters.get("competitor_url")
        competitor_info = parameters.get("competitor_info", {})
        analysis_focus = parameters.get("analysis_focus", ["messaging", "pricing", "features"])

        log = logger.bind(
            tool=self.name,
            has_url=bool(competitor_url),
            analysis_focus=analysis_focus,
        )
        log.info("analyze_competitor_start")

        try:
            # Build analysis prompt
            prompt = self._build_analysis_prompt(
                competitor_url,
                competitor_info,
                analysis_focus,
            )

            # Analyze using Gemini
            messages = [{"role": "user", "content": prompt}]

            analysis_text = await self.gemini_client.chat_completion(
                messages=messages,
                temperature=0.3,
            )

            log.info("analyze_competitor_complete")

            return {
                "success": True,
                "analysis": analysis_text,
                "analysis_focus": analysis_focus,
                "message": "Competitor analysis completed",
            }

        except GeminiError as e:
            log.error("gemini_error", error=str(e))
            raise ToolExecutionError(
                message=f"Competitor analysis failed: {e.message}",
                tool_name=self.name,
                error_code=e.code,
            )

        except Exception as e:
            log.error("unexpected_error", error=str(e), exc_info=True)
            raise ToolExecutionError(
                message=f"Unexpected error: {str(e)}",
                tool_name=self.name,
            )

    def _build_analysis_prompt(
        self,
        competitor_url: str | None,
        competitor_info: dict[str, Any],
        analysis_focus: list[str],
    ) -> str:
        """Build competitor analysis prompt.

        Args:
            competitor_url: Competitor URL
            competitor_info: Competitor information
            analysis_focus: Focus areas

        Returns:
            Analysis prompt
        """
        # Format competitor information
        if competitor_url:
            competitor_text = f"Competitor URL: {competitor_url}"
        else:
            competitor_name = competitor_info.get("name", "Unknown")
            products = competitor_info.get("products", [])
            messaging = competitor_info.get("messaging", "")

            competitor_text = f"""Competitor: {competitor_name}
Products: {', '.join(products)}
Messaging: {messaging}"""

        focus_text = ", ".join(analysis_focus)

        prompt = f"""Analyze this competitor:

{competitor_text}

Focus Areas: {focus_text}

Provide a comprehensive analysis including:

1. Positioning & Messaging:
   - How do they position themselves?
   - What's their unique value proposition?
   - Key messaging themes

2. Strengths:
   - What are they doing well?
   - Competitive advantages

3. Weaknesses:
   - Where are the gaps?
   - Potential vulnerabilities

4. Opportunities for Differentiation:
   - How can we differentiate?
   - Unmet customer needs
   - Market gaps

5. Strategic Recommendations:
   - How should we respond?
   - Areas to compete or avoid

Be specific and actionable in your analysis."""

        return prompt


class AnalyzeTrendsTool(AgentTool):
    """Tool for analyzing market trends using Gemini.

    This tool analyzes market data and identifies emerging trends,
    patterns, and opportunities.
    """

    def __init__(self, gemini_client: GeminiClient | None = None):
        """Initialize the analyze trends tool.

        Args:
            gemini_client: Gemini client for trend analysis
        """
        metadata = ToolMetadata(
            name="analyze_trends_tool",
            description=(
                "Analyze market trends and patterns using AI. "
                "Identifies emerging trends, consumer behavior shifts, "
                "and market opportunities based on data and insights."
            ),
            category=ToolCategory.AGENT_CUSTOM,
            parameters=[
                ToolParameter(
                    name="market_data",
                    type="object",
                    description="Market data including metrics, reports, observations",
                    required=True,
                ),
                ToolParameter(
                    name="industry",
                    type="string",
                    description="Industry or market segment",
                    required=False,
                ),
                ToolParameter(
                    name="time_period",
                    type="string",
                    description="Time period for trend analysis",
                    required=False,
                    default="last_6_months",
                ),
            ],
            returns="object with trend analysis and predictions",
            credit_cost=3.0,
            tags=["market", "trends", "analysis", "ai"],
        )

        super().__init__(metadata)

        self.gemini_client = gemini_client or GeminiClient()

    async def execute(
        self,
        parameters: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute trend analysis.

        Args:
            parameters: Tool parameters
            context: Execution context

        Returns:
            Trend analysis insights

        Raises:
            ToolExecutionError: If analysis fails
        """
        market_data = parameters.get("market_data", {})
        industry = parameters.get("industry")
        time_period = parameters.get("time_period", "last_6_months")

        log = logger.bind(
            tool=self.name,
            industry=industry,
            time_period=time_period,
        )
        log.info("analyze_trends_start")

        try:
            # Build analysis prompt
            prompt = self._build_trends_prompt(market_data, industry, time_period)

            # Analyze using Gemini
            messages = [{"role": "user", "content": prompt}]

            trends_text = await self.gemini_client.chat_completion(
                messages=messages,
                temperature=0.4,
            )

            log.info("analyze_trends_complete")

            return {
                "success": True,
                "trends": trends_text,
                "industry": industry,
                "time_period": time_period,
                "message": "Trend analysis completed",
            }

        except GeminiError as e:
            log.error("gemini_error", error=str(e))
            raise ToolExecutionError(
                message=f"Trend analysis failed: {e.message}",
                tool_name=self.name,
                error_code=e.code,
            )

        except Exception as e:
            log.error("unexpected_error", error=str(e), exc_info=True)
            raise ToolExecutionError(
                message=f"Unexpected error: {str(e)}",
                tool_name=self.name,
            )

    def _build_trends_prompt(
        self,
        market_data: dict[str, Any],
        industry: str | None,
        time_period: str,
    ) -> str:
        """Build trend analysis prompt.

        Args:
            market_data: Market data
            industry: Industry
            time_period: Time period

        Returns:
            Analysis prompt
        """
        # Format market data
        data_summary = self._format_market_data(market_data)

        industry_text = f"\nIndustry: {industry}" if industry else ""

        prompt = f"""Analyze market trends based on this data:

{data_summary}

Time Period: {time_period}{industry_text}

Provide a comprehensive trend analysis:

1. Emerging Trends:
   - What new patterns are emerging?
   - Consumer behavior shifts
   - Technology adoption

2. Growth Areas:
   - Which segments are growing?
   - New opportunities

3. Declining Areas:
   - What's losing momentum?
   - Risks to watch

4. Future Predictions:
   - Where is the market heading?
   - Expected changes in next 6-12 months

5. Strategic Implications:
   - How should businesses respond?
   - Opportunities to capitalize on

Be specific and data-driven in your analysis."""

        return prompt

    def _format_market_data(self, data: dict[str, Any]) -> str:
        """Format market data for prompt.

        Args:
            data: Market data

        Returns:
            Formatted data
        """
        lines = []

        # Format metrics
        if "metrics" in data:
            lines.append("Key Metrics:")
            for key, value in data["metrics"].items():
                lines.append(f"  - {key}: {value}")

        # Format observations
        if "observations" in data:
            lines.append("\nObservations:")
            for obs in data["observations"][:5]:
                lines.append(f"  - {obs}")

        return "\n".join(lines)


class GenerateStrategyTool(AgentTool):
    """Tool for generating marketing strategies using Gemini.

    This tool generates comprehensive marketing strategies based on
    product information, market analysis, and business goals.
    """

    def __init__(self, gemini_client: GeminiClient | None = None):
        """Initialize the generate strategy tool.

        Args:
            gemini_client: Gemini client for strategy generation
        """
        metadata = ToolMetadata(
            name="generate_strategy_tool",
            description=(
                "Generate comprehensive marketing strategies using AI. "
                "Creates detailed go-to-market plans, positioning strategies, "
                "and tactical recommendations based on product and market analysis."
            ),
            category=ToolCategory.AGENT_CUSTOM,
            parameters=[
                ToolParameter(
                    name="product_info",
                    type="object",
                    description="Product information and positioning",
                    required=True,
                ),
                ToolParameter(
                    name="market_analysis",
                    type="object",
                    description="Market and competitor analysis results",
                    required=False,
                ),
                ToolParameter(
                    name="business_goals",
                    type="array",
                    description="Business objectives and goals",
                    required=False,
                    default=["increase_market_share", "build_brand_awareness"],
                ),
                ToolParameter(
                    name="budget",
                    type="number",
                    description="Marketing budget",
                    required=False,
                ),
            ],
            returns="object with comprehensive marketing strategy",
            credit_cost=5.0,
            tags=["market", "strategy", "planning", "ai"],
        )

        super().__init__(metadata)

        self.gemini_client = gemini_client or GeminiClient()

    async def execute(
        self,
        parameters: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute strategy generation.

        Args:
            parameters: Tool parameters
            context: Execution context

        Returns:
            Generated marketing strategy

        Raises:
            ToolExecutionError: If generation fails
        """
        product_info = parameters.get("product_info", {})
        market_analysis = parameters.get("market_analysis", {})
        business_goals = parameters.get("business_goals", ["increase_market_share"])
        budget = parameters.get("budget")

        log = logger.bind(
            tool=self.name,
            business_goals=business_goals,
            has_budget=bool(budget),
        )
        log.info("generate_strategy_start")

        try:
            # Build strategy prompt
            prompt = self._build_strategy_prompt(
                product_info,
                market_analysis,
                business_goals,
                budget,
            )

            # Generate using Gemini
            messages = [{"role": "user", "content": prompt}]

            strategy_text = await self.gemini_client.chat_completion(
                messages=messages,
                temperature=0.5,
            )

            log.info("generate_strategy_complete")

            return {
                "success": True,
                "strategy": strategy_text,
                "business_goals": business_goals,
                "message": "Marketing strategy generated successfully",
            }

        except GeminiError as e:
            log.error("gemini_error", error=str(e))
            raise ToolExecutionError(
                message=f"Strategy generation failed: {e.message}",
                tool_name=self.name,
                error_code=e.code,
            )

        except Exception as e:
            log.error("unexpected_error", error=str(e), exc_info=True)
            raise ToolExecutionError(
                message=f"Unexpected error: {str(e)}",
                tool_name=self.name,
            )

    def _build_strategy_prompt(
        self,
        product_info: dict[str, Any],
        market_analysis: dict[str, Any],
        business_goals: list[str],
        budget: float | None,
    ) -> str:
        """Build strategy generation prompt.

        Args:
            product_info: Product information
            market_analysis: Market analysis
            business_goals: Business goals
            budget: Marketing budget

        Returns:
            Strategy prompt
        """
        # Format product info
        product_name = product_info.get("name", "product")
        description = product_info.get("description", "")
        target_audience = product_info.get("target_audience", "")

        # Format market analysis
        market_summary = str(market_analysis)[:500] if market_analysis else "Not provided"

        # Format goals
        goals_text = ", ".join(business_goals)

        # Format budget
        budget_text = f"\nMarketing Budget: ${budget:,.2f}" if budget else ""

        prompt = f"""Generate a comprehensive marketing strategy for {product_name}.

Product:
- Description: {description}
- Target Audience: {target_audience}

Market Analysis:
{market_summary}

Business Goals: {goals_text}{budget_text}

Create a detailed marketing strategy including:

1. Positioning Strategy:
   - Unique value proposition
   - Key differentiators
   - Brand positioning

2. Target Audience Strategy:
   - Primary and secondary audiences
   - Customer personas
   - Messaging for each segment

3. Channel Strategy:
   - Recommended marketing channels
   - Channel priorities and rationale
   - Budget allocation by channel

4. Content Strategy:
   - Content themes and topics
   - Content formats
   - Publishing cadence

5. Campaign Ideas:
   - 3-5 campaign concepts
   - Expected outcomes
   - Success metrics

6. Implementation Timeline:
   - Phase 1 (0-3 months)
   - Phase 2 (3-6 months)
   - Phase 3 (6-12 months)

7. Success Metrics:
   - KPIs to track
   - Target benchmarks

Make the strategy specific, actionable, and aligned with business goals."""

        return prompt


# Factory function to create all market tools
def create_market_tools(
    gemini_client: GeminiClient | None = None,
) -> list[AgentTool]:
    """Create all market tools.

    Args:
        gemini_client: Gemini client instance

    Returns:
        List of market tools
    """
    return [
        AnalyzeCompetitorTool(gemini_client=gemini_client),
        AnalyzeTrendsTool(gemini_client=gemini_client),
        GenerateStrategyTool(gemini_client=gemini_client),
    ]
