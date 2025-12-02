"""Landing Page Tools for landing page generation and optimization.

This module provides Agent Custom Tools for landing page operations:
- generate_page_content_tool: Generate landing page content using Gemini
- translate_content_tool: Translate content using Gemini
- optimize_copy_tool: Optimize copy for conversions using Gemini

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


class GeneratePageContentTool(AgentTool):
    """Tool for generating landing page content using Gemini.

    This tool generates complete landing page content including
    headlines, sections, and call-to-actions based on product info.
    """

    def __init__(self, gemini_client: GeminiClient | None = None):
        """Initialize the generate page content tool.

        Args:
            gemini_client: Gemini client for content generation
        """
        metadata = ToolMetadata(
            name="generate_page_content_tool",
            description=(
                "Generate complete landing page content using AI. "
                "Creates headlines, hero sections, features, benefits, "
                "testimonials, and call-to-actions based on product information."
            ),
            category=ToolCategory.AGENT_CUSTOM,
            parameters=[
                ToolParameter(
                    name="product_info",
                    type="object",
                    description="Product information including name, description, features, benefits",
                    required=True,
                ),
                ToolParameter(
                    name="template",
                    type="string",
                    description="Landing page template style",
                    required=False,
                    default="modern",
                    enum=["modern", "minimal", "bold", "elegant", "startup"],
                ),
                ToolParameter(
                    name="target_audience",
                    type="string",
                    description="Target audience description",
                    required=False,
                ),
            ],
            returns="object with structured landing page content",
            credit_cost=10.0,
            tags=["landing_page", "content", "generation", "ai"],
        )

        super().__init__(metadata)

        self.gemini_client = gemini_client or GeminiClient()

    async def execute(
        self,
        parameters: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute page content generation.

        Args:
            parameters: Tool parameters
            context: Execution context

        Returns:
            Generated landing page content

        Raises:
            ToolExecutionError: If generation fails
        """
        product_info = parameters.get("product_info", {})
        template = parameters.get("template", "modern")
        target_audience = parameters.get("target_audience")

        log = logger.bind(
            tool=self.name,
            template=template,
            has_target_audience=bool(target_audience),
        )
        log.info("generate_page_content_start")

        try:
            # Build generation prompt
            prompt = self._build_content_prompt(product_info, template, target_audience)

            # Generate using Gemini
            messages = [{"role": "user", "content": prompt}]

            content_text = await self.gemini_client.chat_completion(
                messages=messages,
                temperature=0.6,
            )

            log.info("generate_page_content_complete")

            return {
                "success": True,
                "content": content_text,
                "template": template,
                "message": "Landing page content generated successfully",
            }

        except GeminiError as e:
            log.error("gemini_error", error=str(e))
            raise ToolExecutionError(
                message=f"Page content generation failed: {e.message}",
                tool_name=self.name,
                error_code=e.code,
            )

        except Exception as e:
            log.error("unexpected_error", error=str(e), exc_info=True)
            raise ToolExecutionError(
                message=f"Unexpected error: {str(e)}",
                tool_name=self.name,
            )

    def _build_content_prompt(
        self,
        product_info: dict[str, Any],
        template: str,
        target_audience: str | None,
    ) -> str:
        """Build content generation prompt.

        Args:
            product_info: Product information
            template: Template style
            target_audience: Target audience

        Returns:
            Generation prompt
        """
        product_name = product_info.get("name", "product")
        description = product_info.get("description", "")
        features = product_info.get("features", [])
        benefits = product_info.get("benefits", [])

        audience_text = f"\nTarget Audience: {target_audience}" if target_audience else ""

        prompt = f"""Generate complete landing page content for {product_name}.

Product Description: {description}

Key Features:
{chr(10).join(f'- {feature}' for feature in features[:5])}

Key Benefits:
{chr(10).join(f'- {benefit}' for benefit in benefits[:5])}{audience_text}

Template Style: {template}

Generate the following sections:

1. Hero Section:
   - Compelling headline (8-12 words)
   - Subheadline (15-25 words)
   - Primary CTA button text

2. Problem Statement:
   - What problem does this solve? (2-3 sentences)

3. Solution Overview:
   - How does this product solve it? (2-3 sentences)

4. Features Section:
   - 3-5 feature blocks with titles and descriptions

5. Benefits Section:
   - 3-5 benefit statements with explanations

6. Social Proof:
   - 2-3 testimonial templates

7. Final CTA:
   - Compelling call-to-action section

Make the content persuasive, clear, and conversion-focused."""

        return prompt


class TranslateContentTool(AgentTool):
    """Tool for translating content using Gemini.

    This tool translates landing page content while maintaining
    tone, style, and marketing effectiveness.
    """

    def __init__(self, gemini_client: GeminiClient | None = None):
        """Initialize the translate content tool.

        Args:
            gemini_client: Gemini client for translation
        """
        metadata = ToolMetadata(
            name="translate_content_tool",
            description=(
                "Translate landing page content using AI. "
                "Maintains tone, style, and marketing effectiveness "
                "while adapting to target language and culture."
            ),
            category=ToolCategory.AGENT_CUSTOM,
            parameters=[
                ToolParameter(
                    name="content",
                    type="string",
                    description="Content to translate",
                    required=True,
                ),
                ToolParameter(
                    name="target_language",
                    type="string",
                    description="Target language code (e.g., 'zh', 'es', 'fr')",
                    required=True,
                ),
                ToolParameter(
                    name="source_language",
                    type="string",
                    description="Source language code (default: 'en')",
                    required=False,
                    default="en",
                ),
                ToolParameter(
                    name="maintain_tone",
                    type="boolean",
                    description="Whether to maintain original tone and style",
                    required=False,
                    default=True,
                ),
            ],
            returns="object with translated content",
            credit_cost=3.0,
            tags=["landing_page", "translation", "localization", "ai"],
        )

        super().__init__(metadata)

        self.gemini_client = gemini_client or GeminiClient()

    async def execute(
        self,
        parameters: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute content translation.

        Args:
            parameters: Tool parameters
            context: Execution context

        Returns:
            Translated content

        Raises:
            ToolExecutionError: If translation fails
        """
        content = parameters.get("content", "")
        target_language = parameters.get("target_language")
        source_language = parameters.get("source_language", "en")
        maintain_tone = parameters.get("maintain_tone", True)

        log = logger.bind(
            tool=self.name,
            source_language=source_language,
            target_language=target_language,
            maintain_tone=maintain_tone,
        )
        log.info("translate_content_start")

        try:
            # Build translation prompt
            prompt = self._build_translation_prompt(
                content,
                source_language,
                target_language,
                maintain_tone,
            )

            # Translate using Gemini
            messages = [{"role": "user", "content": prompt}]

            translated_text = await self.gemini_client.chat_completion(
                messages=messages,
                temperature=0.3,
            )

            log.info("translate_content_complete")

            return {
                "success": True,
                "translated_content": translated_text,
                "source_language": source_language,
                "target_language": target_language,
                "message": f"Content translated to {target_language}",
            }

        except GeminiError as e:
            log.error("gemini_error", error=str(e))
            raise ToolExecutionError(
                message=f"Content translation failed: {e.message}",
                tool_name=self.name,
                error_code=e.code,
            )

        except Exception as e:
            log.error("unexpected_error", error=str(e), exc_info=True)
            raise ToolExecutionError(
                message=f"Unexpected error: {str(e)}",
                tool_name=self.name,
            )

    def _build_translation_prompt(
        self,
        content: str,
        source_language: str,
        target_language: str,
        maintain_tone: bool,
    ) -> str:
        """Build translation prompt.

        Args:
            content: Content to translate
            source_language: Source language
            target_language: Target language
            maintain_tone: Whether to maintain tone

        Returns:
            Translation prompt
        """
        tone_instruction = ""
        if maintain_tone:
            tone_instruction = """
Important: Maintain the original tone, style, and marketing effectiveness.
Adapt idioms and cultural references appropriately for the target audience."""

        prompt = f"""Translate the following marketing content from {source_language} to {target_language}.

Content:
{content}{tone_instruction}

Provide a natural, culturally appropriate translation that maintains marketing impact."""

        return prompt


class OptimizeCopyTool(AgentTool):
    """Tool for optimizing copy for conversions using Gemini.

    This tool analyzes and optimizes landing page copy to improve
    conversion rates and engagement.
    """

    def __init__(self, gemini_client: GeminiClient | None = None):
        """Initialize the optimize copy tool.

        Args:
            gemini_client: Gemini client for optimization
        """
        metadata = ToolMetadata(
            name="optimize_copy_tool",
            description=(
                "Optimize landing page copy for better conversions using AI. "
                "Analyzes current copy and provides improved versions "
                "with better clarity, persuasion, and call-to-actions."
            ),
            category=ToolCategory.AGENT_CUSTOM,
            parameters=[
                ToolParameter(
                    name="content",
                    type="string",
                    description="Current landing page copy",
                    required=True,
                ),
                ToolParameter(
                    name="optimization_goal",
                    type="string",
                    description="Primary optimization goal",
                    required=False,
                    default="conversions",
                    enum=["conversions", "clarity", "engagement", "trust"],
                ),
                ToolParameter(
                    name="target_audience",
                    type="string",
                    description="Target audience description",
                    required=False,
                ),
            ],
            returns="object with optimized copy and improvement suggestions",
            credit_cost=3.0,
            tags=["landing_page", "optimization", "copywriting", "ai"],
        )

        super().__init__(metadata)

        self.gemini_client = gemini_client or GeminiClient()

    async def execute(
        self,
        parameters: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute copy optimization.

        Args:
            parameters: Tool parameters
            context: Execution context

        Returns:
            Optimized copy and suggestions

        Raises:
            ToolExecutionError: If optimization fails
        """
        content = parameters.get("content", "")
        optimization_goal = parameters.get("optimization_goal", "conversions")
        target_audience = parameters.get("target_audience")

        log = logger.bind(
            tool=self.name,
            optimization_goal=optimization_goal,
            has_target_audience=bool(target_audience),
        )
        log.info("optimize_copy_start")

        try:
            # Build optimization prompt
            prompt = self._build_optimization_prompt(
                content,
                optimization_goal,
                target_audience,
            )

            # Optimize using Gemini
            messages = [{"role": "user", "content": prompt}]

            optimized_text = await self.gemini_client.chat_completion(
                messages=messages,
                temperature=0.5,
            )

            log.info("optimize_copy_complete")

            return {
                "success": True,
                "optimized_copy": optimized_text,
                "optimization_goal": optimization_goal,
                "message": "Copy optimized successfully",
            }

        except GeminiError as e:
            log.error("gemini_error", error=str(e))
            raise ToolExecutionError(
                message=f"Copy optimization failed: {e.message}",
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
        content: str,
        optimization_goal: str,
        target_audience: str | None,
    ) -> str:
        """Build optimization prompt.

        Args:
            content: Current copy
            optimization_goal: Optimization goal
            target_audience: Target audience

        Returns:
            Optimization prompt
        """
        audience_text = f"\nTarget Audience: {target_audience}" if target_audience else ""

        goal_descriptions = {
            "conversions": "maximize conversion rate and drive action",
            "clarity": "improve clarity and understanding",
            "engagement": "increase engagement and time on page",
            "trust": "build trust and credibility",
        }

        goal_desc = goal_descriptions.get(optimization_goal, optimization_goal)

        prompt = f"""Optimize this landing page copy to {goal_desc}.

Current Copy:
{content}{audience_text}

Provide:
1. Optimized Version: Improved copy with specific changes
2. Key Improvements: What was changed and why
3. A/B Test Suggestions: Alternative versions to test
4. Additional Recommendations: Other ways to improve

Focus on:
- Clear value proposition
- Compelling headlines
- Strong call-to-actions
- Persuasive language
- Removing friction"""

        return prompt


# Factory function to create all landing page tools
def create_landing_page_tools(
    gemini_client: GeminiClient | None = None,
) -> list[AgentTool]:
    """Create all landing page tools.

    Args:
        gemini_client: Gemini client instance

    Returns:
        List of landing page tools
    """
    return [
        GeneratePageContentTool(gemini_client=gemini_client),
        TranslateContentTool(gemini_client=gemini_client),
        OptimizeCopyTool(gemini_client=gemini_client),
    ]
