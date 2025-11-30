"""
Copy Optimizer for Landing Page module.

Uses Gemini 2.5 Pro to optimize landing page copy for better conversion rates.
Supports different optimization goals and section-specific optimization.

Requirements: 4.1, 4.4, 4.5
"""

import structlog
from pydantic import BaseModel, Field

from app.services.gemini_client import GeminiClient, GeminiError
from ..models import OptimizationResult

logger = structlog.get_logger(__name__)


class CopyOptimizationResponse(BaseModel):
    """Structured response from AI for copy optimization."""

    optimized_text: str = Field(description="The optimized copy text")
    improvements: list[str] = Field(
        description="List of improvements made to the copy"
    )
    confidence_score: float = Field(
        ge=0, le=1, description="Confidence score for the optimization (0-1)"
    )


class CopyOptimizer:
    """Copy Optimizer.

    Optimizes landing page copy using Gemini 2.5 Pro AI model.
    Supports different sections (hero, cta, features) and optimization goals.

    Requirements: 4.1, 4.4, 4.5
    """

    # Supported sections for optimization
    SUPPORTED_SECTIONS = ["hero", "cta", "features", "subheadline", "description"]

    # Supported optimization goals
    SUPPORTED_GOALS = [
        "increase_conversion",
        "emotional_appeal",
        "urgency",
        "clarity",
        "trust",
    ]

    # Section-specific optimization prompts
    SECTION_PROMPTS = {
        "hero": """You are optimizing a landing page HERO HEADLINE.
Focus on:
- Creating immediate emotional impact
- Communicating the core value proposition clearly
- Using power words that drive action
- Keeping it concise (under 10 words ideal)""",
        "cta": """You are optimizing a CALL-TO-ACTION button text.
Focus on:
- Using action-oriented verbs (Get, Start, Discover, Claim)
- Creating urgency without being pushy
- Highlighting the benefit of clicking
- Keeping it short (2-5 words ideal)""",
        "features": """You are optimizing a FEATURE description.
Focus on:
- Highlighting benefits over features
- Using specific, concrete language
- Making it scannable and easy to read
- Connecting to user pain points""",
        "subheadline": """You are optimizing a SUBHEADLINE.
Focus on:
- Supporting and expanding on the headline
- Adding specific details or proof points
- Building credibility and trust
- Keeping it under 20 words""",
        "description": """You are optimizing a PRODUCT DESCRIPTION.
Focus on:
- Highlighting key benefits
- Using sensory and emotional language
- Including social proof elements
- Making it scannable with clear structure""",
    }

    # Goal-specific optimization instructions
    GOAL_INSTRUCTIONS = {
        "increase_conversion": """Optimization goal: INCREASE CONVERSION
- Add urgency elements (limited time, scarcity)
- Include clear value proposition
- Remove friction words
- Add social proof hints if appropriate""",
        "emotional_appeal": """Optimization goal: EMOTIONAL APPEAL
- Use emotionally charged words
- Connect to user aspirations and desires
- Paint a picture of the transformed state
- Use sensory language""",
        "urgency": """Optimization goal: CREATE URGENCY
- Add time-sensitive language
- Imply scarcity or exclusivity
- Use action-oriented verbs
- Create fear of missing out (FOMO)""",
        "clarity": """Optimization goal: IMPROVE CLARITY
- Simplify complex language
- Use shorter sentences
- Remove jargon and buzzwords
- Make the message crystal clear""",
        "trust": """Optimization goal: BUILD TRUST
- Add credibility indicators
- Use confident but not aggressive language
- Include specifics and numbers
- Remove hyperbole and exaggeration""",
    }

    def __init__(self, gemini_client: GeminiClient | None = None):
        """Initialize CopyOptimizer.

        Args:
            gemini_client: Gemini client for AI generation. If None, creates new instance.
        """
        self.gemini_client = gemini_client or GeminiClient()

    async def optimize(
        self,
        current_text: str,
        section: str = "hero",
        optimization_goal: str = "increase_conversion",
        context: dict | None = None,
    ) -> OptimizationResult:
        """Optimize copy text.

        Uses Gemini 2.5 Pro to optimize the provided copy based on section type
        and optimization goal. Returns original text on failure (fallback behavior).

        Args:
            current_text: Current copy text to optimize
            section: Section type (hero, cta, features, subheadline, description)
            optimization_goal: Optimization goal (increase_conversion, emotional_appeal, etc.)
            context: Optional context with additional information (product_info, etc.)

        Returns:
            OptimizationResult with optimized_text, improvements, and confidence_score

        Requirements: 4.1, 4.4, 4.5
        """
        log = logger.bind(
            section=section,
            optimization_goal=optimization_goal,
            text_length=len(current_text),
        )

        log.info("copy_optimization_start")

        # Validate inputs
        if not current_text or not current_text.strip():
            log.warning("copy_optimization_empty_text")
            return OptimizationResult(
                optimized_text=current_text or "",
                improvements=[],
                confidence_score=0.0,
                fallback=True,
            )

        # Normalize section and goal
        section = section.lower() if section else "hero"
        optimization_goal = optimization_goal.lower() if optimization_goal else "increase_conversion"

        # Use default prompts for unsupported sections/goals
        section_prompt = self.SECTION_PROMPTS.get(
            section, self.SECTION_PROMPTS["description"]
        )
        goal_instruction = self.GOAL_INSTRUCTIONS.get(
            optimization_goal, self.GOAL_INSTRUCTIONS["increase_conversion"]
        )

        try:
            # Build the optimization prompt
            prompt = self._build_optimization_prompt(
                current_text=current_text,
                section_prompt=section_prompt,
                goal_instruction=goal_instruction,
                context=context,
            )

            # Call Gemini 2.5 Pro for optimization
            result = await self.gemini_client.structured_output(
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert copywriter specializing in high-converting landing pages.
Your task is to optimize the given copy while maintaining its core message.
Always provide specific, actionable improvements.""",
                    },
                    {"role": "user", "content": prompt},
                ],
                schema=CopyOptimizationResponse,
                temperature=0.7,  # Allow some creativity
            )

            log.info(
                "copy_optimization_success",
                improvements_count=len(result.improvements),
                confidence=result.confidence_score,
            )

            return OptimizationResult(
                optimized_text=result.optimized_text,
                improvements=result.improvements,
                confidence_score=result.confidence_score,
                fallback=False,
            )

        except GeminiError as e:
            log.error(
                "copy_optimization_gemini_error",
                error=str(e),
                error_code=e.code,
            )
            # Fallback: return original text
            return self._create_fallback_result(current_text)

        except Exception as e:
            log.error(
                "copy_optimization_unexpected_error",
                error=str(e),
                exc_info=True,
            )
            # Fallback: return original text
            return self._create_fallback_result(current_text)

    def _build_optimization_prompt(
        self,
        current_text: str,
        section_prompt: str,
        goal_instruction: str,
        context: dict | None = None,
    ) -> str:
        """Build the optimization prompt for the AI model.

        Args:
            current_text: The text to optimize
            section_prompt: Section-specific instructions
            goal_instruction: Goal-specific instructions
            context: Optional additional context

        Returns:
            Complete prompt string
        """
        context_section = ""
        if context:
            product_info = context.get("product_info", {})
            if product_info:
                context_section = f"""
Product Context:
- Product: {product_info.get('title', 'N/A')}
- Price: {product_info.get('currency', 'USD')} {product_info.get('price', 'N/A')}
- Key Features: {', '.join(product_info.get('features', [])[:3]) or 'N/A'}
"""

        return f"""{section_prompt}

{goal_instruction}

{context_section}
Current copy to optimize:
"{current_text}"

Please optimize this copy and provide:
1. The optimized text
2. A list of specific improvements you made
3. A confidence score (0-1) indicating how much better the optimized version is

Keep the optimized text similar in length to the original unless brevity improves it.
Maintain the core message while enhancing its effectiveness."""

    def _create_fallback_result(self, original_text: str) -> OptimizationResult:
        """Create a fallback result with the original text.

        Args:
            original_text: The original text to return

        Returns:
            OptimizationResult with fallback=True
        """
        return OptimizationResult(
            optimized_text=original_text,
            improvements=[],
            confidence_score=0.0,
            fallback=True,
        )
