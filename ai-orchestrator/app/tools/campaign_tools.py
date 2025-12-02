"""Campaign Tools for advertising campaign management.

This module provides Agent Custom Tools for campaign-related operations:
- optimize_budget_tool: AI-powered budget optimization using Gemini
- generate_ad_copy_tool: Generate ad copy using Gemini
- suggest_targeting_tool: Suggest audience targeting using Gemini

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


class OptimizeBudgetTool(AgentTool):
    """Tool for AI-powered budget optimization using Gemini.

    This tool analyzes campaign performance and provides budget
    allocation recommendations to maximize ROI.
    """

    def __init__(self, gemini_client: GeminiClient | None = None):
        """Initialize the optimize budget tool.

        Args:
            gemini_client: Gemini client for optimization
        """
        metadata = ToolMetadata(
            name="optimize_budget_tool",
            description=(
                "Optimize advertising budget allocation using AI. "
                "Analyzes campaign performance and provides recommendations "
                "for budget distribution to maximize ROI."
            ),
            category=ToolCategory.AGENT_CUSTOM,
            parameters=[
                ToolParameter(
                    name="performance_data",
                    type="object",
                    description="Campaign performance data with spend and results",
                    required=True,
                ),
                ToolParameter(
                    name="total_budget",
                    type="number",
                    description="Total budget to allocate",
                    required=True,
                ),
                ToolParameter(
                    name="optimization_goal",
                    type="string",
                    description="Optimization objective",
                    required=False,
                    default="maximize_roas",
                    enum=["maximize_roas", "minimize_cpa", "maximize_conversions"],
                ),
            ],
            returns="object with budget allocation recommendations",
            credit_cost=3.0,
            tags=["campaign", "budget", "optimization", "ai"],
        )

        super().__init__(metadata)

        self.gemini_client = gemini_client or GeminiClient()

    async def execute(
        self,
        parameters: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute budget optimization.

        Args:
            parameters: Tool parameters
            context: Execution context

        Returns:
            Budget allocation recommendations

        Raises:
            ToolExecutionError: If optimization fails
        """
        performance_data = parameters.get("performance_data", {})
        total_budget = parameters.get("total_budget")
        optimization_goal = parameters.get("optimization_goal", "maximize_roas")

        log = logger.bind(
            tool=self.name,
            total_budget=total_budget,
            optimization_goal=optimization_goal,
        )
        log.info("optimize_budget_start")

        try:
            # Build optimization prompt
            prompt = self._build_optimization_prompt(
                performance_data,
                total_budget,
                optimization_goal,
            )

            # Optimize using Gemini
            messages = [{"role": "user", "content": prompt}]

            optimization_text = await self.gemini_client.chat_completion(
                messages=messages,
                temperature=0.3,
            )

            log.info("optimize_budget_complete")

            return {
                "success": True,
                "recommendations": optimization_text,
                "total_budget": total_budget,
                "optimization_goal": optimization_goal,
                "message": "Budget optimization completed",
            }

        except GeminiError as e:
            log.error("gemini_error", error=str(e))
            raise ToolExecutionError(
                message=f"Budget optimization failed: {e.message}",
                tool_name=self.name,
                error_code=e.code,
            )

        except Exception as e:
            log.error("unexpected_error", error=str(e), exc_info=True)
            raise ToolExecutionError(
                message=f"Unexpected error: {str(e)}",
                tool_name=self.name,
            )

    def _build_optimization_prompt(
        self,
        performance_data: dict[str, Any],
        total_budget: float,
        optimization_goal: str,
    ) -> str:
        """Build budget optimization prompt.

        Args:
            performance_data: Campaign performance data
            total_budget: Total budget
            optimization_goal: Optimization goal

        Returns:
            Optimization prompt
        """
        # Format performance data
        data_summary = self._format_performance_data(performance_data)

        goal_descriptions = {
            "maximize_roas": "maximize Return on Ad Spend (ROAS)",
            "minimize_cpa": "minimize Cost Per Acquisition (CPA)",
            "maximize_conversions": "maximize total conversions",
        }

        goal_desc = goal_descriptions.get(optimization_goal, optimization_goal)

        prompt = f"""Optimize budget allocation for these advertising campaigns:

{data_summary}

Total Budget: ${total_budget}
Optimization Goal: {goal_desc}

Provide specific budget allocation recommendations:

For each campaign, specify:
1. Recommended Budget: Dollar amount
2. Rationale: Why this allocation
3. Expected Results: Projected performance
4. Confidence Level: High/Medium/Low

Also provide:
- Overall strategy explanation
- Risk factors to consider
- Alternative allocation scenarios"""

        return prompt

    def _format_performance_data(self, data: dict[str, Any]) -> str:
        """Format performance data for prompt.

        Args:
            data: Performance data

        Returns:
            Formatted data
        """
        lines = []

        if "campaigns" in data:
            lines.append("Campaign Performance:")
            for campaign in data["campaigns"]:
                name = campaign.get("name", "Unknown")
                spend = campaign.get("spend", 0)
                revenue = campaign.get("revenue", 0)
                conversions = campaign.get("conversions", 0)
                roas = revenue / spend if spend > 0 else 0

                lines.append(
                    f"  - {name}: Spend ${spend}, Revenue ${revenue}, "
                    f"Conversions {conversions}, ROAS {roas:.2f}"
                )

        return "\n".join(lines)


class GenerateAdCopyTool(AgentTool):
    """Tool for generating ad copy using Gemini.

    This tool generates compelling ad copy based on product
    information and target audience.
    """

    def __init__(self, gemini_client: GeminiClient | None = None):
        """Initialize the generate ad copy tool.

        Args:
            gemini_client: Gemini client for copy generation
        """
        metadata = ToolMetadata(
            name="generate_ad_copy_tool",
            description=(
                "Generate compelling advertising copy using AI. "
                "Creates headlines, descriptions, and call-to-actions "
                "tailored to your product and target audience."
            ),
            category=ToolCategory.AGENT_CUSTOM,
            parameters=[
                ToolParameter(
                    name="product_info",
                    type="object",
                    description="Product information including name, features, benefits",
                    required=True,
                ),
                ToolParameter(
                    name="platform",
                    type="string",
                    description="Advertising platform",
                    required=False,
                    default="facebook",
                    enum=["facebook", "instagram", "tiktok", "google"],
                ),
                ToolParameter(
                    name="tone",
                    type="string",
                    description="Copy tone and style",
                    required=False,
                    default="professional",
                    enum=["professional", "casual", "urgent", "friendly", "luxury"],
                ),
                ToolParameter(
                    name="count",
                    type="number",
                    description="Number of variations to generate",
                    required=False,
                    default=3,
                ),
            ],
            returns="object with generated ad copy variations",
            credit_cost=2.0,
            tags=["campaign", "copy", "generation", "ai"],
        )

        super().__init__(metadata)

        self.gemini_client = gemini_client or GeminiClient()

    async def execute(
        self,
        parameters: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute ad copy generation.

        Args:
            parameters: Tool parameters
            context: Execution context

        Returns:
            Generated ad copy variations

        Raises:
            ToolExecutionError: If generation fails
        """
        product_info = parameters.get("product_info", {})
        platform = parameters.get("platform", "facebook")
        tone = parameters.get("tone", "professional")
        count = parameters.get("count", 3)

        log = logger.bind(
            tool=self.name,
            platform=platform,
            tone=tone,
            count=count,
        )
        log.info("generate_ad_copy_start")

        try:
            # Build generation prompt
            prompt = self._build_copy_prompt(product_info, platform, tone, count)

            # Generate using Gemini
            messages = [{"role": "user", "content": prompt}]

            copy_text = await self.gemini_client.chat_completion(
                messages=messages,
                temperature=0.7,
            )

            log.info("generate_ad_copy_complete")

            return {
                "success": True,
                "ad_copy": copy_text,
                "platform": platform,
                "tone": tone,
                "message": f"Generated {count} ad copy variations",
            }

        except GeminiError as e:
            log.error("gemini_error", error=str(e))
            raise ToolExecutionError(
                message=f"Ad copy generation failed: {e.message}",
                tool_name=self.name,
                error_code=e.code,
            )

        except Exception as e:
            log.error("unexpected_error", error=str(e), exc_info=True)
            raise ToolExecutionError(
                message=f"Unexpected error: {str(e)}",
                tool_name=self.name,
            )

    def _build_copy_prompt(
        self,
        product_info: dict[str, Any],
        platform: str,
        tone: str,
        count: int,
    ) -> str:
        """Build ad copy generation prompt.

        Args:
            product_info: Product information
            platform: Advertising platform
            tone: Copy tone
            count: Number of variations

        Returns:
            Generation prompt
        """
        product_name = product_info.get("name", "product")
        description = product_info.get("description", "")
        features = product_info.get("features", [])
        target_audience = product_info.get("target_audience", "general audience")

        # Platform-specific requirements
        platform_specs = {
            "facebook": "Headline (40 chars), Primary Text (125 chars), Description (30 chars)",
            "instagram": "Caption (2200 chars), focus on visual storytelling",
            "tiktok": "Short, catchy text (100 chars), trending language",
            "google": "Headline (30 chars), Description (90 chars), concise and keyword-rich",
        }

        specs = platform_specs.get(platform, "Standard ad copy format")

        # Tone descriptions
        tone_descriptions = {
            "professional": "professional, trustworthy, authoritative",
            "casual": "friendly, conversational, relatable",
            "urgent": "time-sensitive, action-oriented, compelling",
            "friendly": "warm, approachable, helpful",
            "luxury": "premium, exclusive, sophisticated",
        }

        tone_desc = tone_descriptions.get(tone, tone)

        prompt = f"""Generate {count} variations of advertising copy for {product_name}.

Product Description: {description}

Key Features:
{chr(10).join(f'- {feature}' for feature in features[:5])}

Target Audience: {target_audience}
Platform: {platform} ({specs})
Tone: {tone_desc}

For each variation, provide:
1. Headline: Attention-grabbing main message
2. Body Text: Compelling description
3. Call-to-Action: Clear next step

Make each variation unique and compelling."""

        return prompt


class SuggestTargetingTool(AgentTool):
    """Tool for suggesting audience targeting using Gemini.

    This tool analyzes product information and suggests optimal
    audience targeting parameters for advertising campaigns.
    """

    def __init__(self, gemini_client: GeminiClient | None = None):
        """Initialize the suggest targeting tool.

        Args:
            gemini_client: Gemini client for targeting suggestions
        """
        metadata = ToolMetadata(
            name="suggest_targeting_tool",
            description=(
                "Suggest optimal audience targeting for advertising campaigns. "
                "Analyzes product information and recommends demographics, "
                "interests, behaviors, and other targeting parameters."
            ),
            category=ToolCategory.AGENT_CUSTOM,
            parameters=[
                ToolParameter(
                    name="product_info",
                    type="object",
                    description="Product information including category, price, features",
                    required=True,
                ),
                ToolParameter(
                    name="platform",
                    type="string",
                    description="Advertising platform",
                    required=False,
                    default="facebook",
                    enum=["facebook", "instagram", "tiktok", "google"],
                ),
                ToolParameter(
                    name="campaign_goal",
                    type="string",
                    description="Campaign objective",
                    required=False,
                    default="conversions",
                    enum=["awareness", "consideration", "conversions"],
                ),
            ],
            returns="object with targeting recommendations",
            credit_cost=2.0,
            tags=["campaign", "targeting", "audience", "ai"],
        )

        super().__init__(metadata)

        self.gemini_client = gemini_client or GeminiClient()

    async def execute(
        self,
        parameters: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute targeting suggestion.

        Args:
            parameters: Tool parameters
            context: Execution context

        Returns:
            Targeting recommendations

        Raises:
            ToolExecutionError: If suggestion fails
        """
        product_info = parameters.get("product_info", {})
        platform = parameters.get("platform", "facebook")
        campaign_goal = parameters.get("campaign_goal", "conversions")

        log = logger.bind(
            tool=self.name,
            platform=platform,
            campaign_goal=campaign_goal,
        )
        log.info("suggest_targeting_start")

        try:
            # Build suggestion prompt
            prompt = self._build_targeting_prompt(product_info, platform, campaign_goal)

            # Generate suggestions using Gemini
            messages = [{"role": "user", "content": prompt}]

            targeting_text = await self.gemini_client.chat_completion(
                messages=messages,
                temperature=0.4,
            )

            log.info("suggest_targeting_complete")

            return {
                "success": True,
                "targeting_recommendations": targeting_text,
                "platform": platform,
                "campaign_goal": campaign_goal,
                "message": "Targeting recommendations generated",
            }

        except GeminiError as e:
            log.error("gemini_error", error=str(e))
            raise ToolExecutionError(
                message=f"Targeting suggestion failed: {e.message}",
                tool_name=self.name,
                error_code=e.code,
            )

        except Exception as e:
            log.error("unexpected_error", error=str(e), exc_info=True)
            raise ToolExecutionError(
                message=f"Unexpected error: {str(e)}",
                tool_name=self.name,
            )

    def _build_targeting_prompt(
        self,
        product_info: dict[str, Any],
        platform: str,
        campaign_goal: str,
    ) -> str:
        """Build targeting suggestion prompt.

        Args:
            product_info: Product information
            platform: Advertising platform
            campaign_goal: Campaign goal

        Returns:
            Suggestion prompt
        """
        product_name = product_info.get("name", "product")
        category = product_info.get("category", "")
        price_range = product_info.get("price_range", "")
        description = product_info.get("description", "")

        prompt = f"""Suggest optimal audience targeting for advertising this product:

Product: {product_name}
Category: {category}
Price Range: {price_range}
Description: {description}

Platform: {platform}
Campaign Goal: {campaign_goal}

Provide detailed targeting recommendations:

1. Demographics:
   - Age range
   - Gender
   - Location
   - Language

2. Interests:
   - Primary interests
   - Related interests
   - Behaviors

3. Custom Audiences:
   - Lookalike audiences
   - Retargeting strategies

4. Exclusions:
   - Who to exclude and why

5. Budget Allocation:
   - Recommended audience size
   - Expected reach

Be specific and platform-appropriate in your recommendations."""

        return prompt


# Factory function to create all campaign tools
def create_campaign_tools(
    gemini_client: GeminiClient | None = None,
) -> list[AgentTool]:
    """Create all campaign tools.

    Args:
        gemini_client: Gemini client instance

    Returns:
        List of campaign tools
    """
    return [
        OptimizeBudgetTool(gemini_client=gemini_client),
        GenerateAdCopyTool(gemini_client=gemini_client),
        SuggestTargetingTool(gemini_client=gemini_client),
    ]
