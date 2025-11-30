"""
Creative scoring engine using Gemini 2.5 Flash.

Requirements: 7.1, 7.2, 7.3

This module implements multi-dimensional AI evaluation of creative assets
using Google's Gemini 2.5 Flash model for fast, accurate scoring.
"""

from typing import TYPE_CHECKING

import structlog
from pydantic import BaseModel, Field

from ..models import CreativeScore, DimensionScore

if TYPE_CHECKING:
    from app.services.gemini_client import GeminiClient

logger = structlog.get_logger(__name__)


class DimensionAnalysis(BaseModel):
    """AI analysis result for a single dimension."""

    score: float = Field(ge=0, le=100, description="Score from 0-100")
    analysis: str = Field(description="Analysis explanation in Chinese")


class ScoringAnalysisResult(BaseModel):
    """Structured output schema for Gemini scoring analysis."""

    visual_impact: DimensionAnalysis = Field(
        description="视觉冲击力评分：画面是否吸引眼球、主体是否突出"
    )
    composition: DimensionAnalysis = Field(
        description="构图平衡评分：元素布局是否合理、视觉重心是否稳定"
    )
    color_harmony: DimensionAnalysis = Field(
        description="色彩和谐评分：配色是否协调、对比度是否适中"
    )
    text_clarity: DimensionAnalysis = Field(
        description="文案清晰评分：文字是否可读、信息是否清晰（无文字则默认满分）"
    )
    overall_analysis: str = Field(description="AI 综合分析说明")


class ScoringEngine:
    """Scores creative assets using multi-dimensional AI evaluation.

    Evaluates creatives on four dimensions:
    - Visual Impact (30%): Eye-catching, prominent subject
    - Composition (25%): Balanced layout, stable visual weight
    - Color Harmony (25%): Coordinated colors, appropriate contrast
    - Text Clarity (20%): Readable text, clear information

    Uses Gemini 2.5 Flash for fast AI analysis with structured output.
    """

    DIMENSION_WEIGHTS = {
        "visual_impact": 0.30,
        "composition": 0.25,
        "color_harmony": 0.25,
        "text_clarity": 0.20,
    }

    SCORING_PROMPT = """你是一位专业的广告素材评审专家。请分析这张广告图片，并从以下四个维度进行评分（0-100分）：

1. **视觉冲击力 (Visual Impact)** - 权重 30%
   - 画面是否吸引眼球
   - 主体是否突出
   - 整体视觉效果是否强烈

2. **构图平衡 (Composition)** - 权重 25%
   - 元素布局是否合理
   - 视觉重心是否稳定
   - 空间利用是否得当

3. **色彩和谐 (Color Harmony)** - 权重 25%
   - 配色是否协调
   - 对比度是否适中
   - 色彩是否符合品牌调性

4. **文案清晰 (Text Clarity)** - 权重 20%
   - 文字是否可读
   - 信息是否清晰
   - 文案与画面是否协调
   - 注意：如果图片中没有文字，此项默认给100分

请为每个维度提供：
- 具体分数（0-100）
- 简短的分析说明（中文）

最后提供一段综合分析，总结这张素材的优缺点和改进建议。

图片URL: {image_url}"""

    def __init__(self, gemini_client: "GeminiClient | None" = None):
        """Initialize scoring engine.

        Args:
            gemini_client: Gemini client for AI analysis. If None, will be
                          created when needed.
        """
        self.gemini = gemini_client
        self._log = logger.bind(component="scoring_engine")

    def _get_gemini_client(self) -> "GeminiClient":
        """Get or create Gemini client.

        Returns:
            GeminiClient instance

        Raises:
            ValueError: If no client available and cannot create one
        """
        if self.gemini is not None:
            return self.gemini

        # Lazy import to avoid circular dependencies
        from app.services.gemini_client import GeminiClient

        self.gemini = GeminiClient()
        return self.gemini

    async def score(self, image_url: str) -> CreativeScore:
        """Score a creative image using AI multi-dimensional evaluation.

        Calls Gemini 2.5 Flash to analyze the image and score it on four
        dimensions: visual impact, composition, color harmony, and text clarity.
        Returns a weighted total score along with individual dimension scores.

        Args:
            image_url: URL of the image to score

        Returns:
            CreativeScore with total score, dimension scores, and AI analysis

        Raises:
            GeminiError: If AI analysis fails after retries
            ValueError: If image_url is empty
        """
        if not image_url:
            raise ValueError("image_url cannot be empty")

        log = self._log.bind(image_url=image_url)
        log.info("scoring_start")

        gemini = self._get_gemini_client()

        # Build the prompt with image URL
        prompt = self.SCORING_PROMPT.format(image_url=image_url)

        # Use fast_structured_output for Gemini 2.5 Flash with structured response
        messages = [
            {
                "role": "user",
                "content": prompt,
            }
        ]

        try:
            result: ScoringAnalysisResult = await gemini.fast_structured_output(
                messages=messages,
                schema=ScoringAnalysisResult,
                temperature=0.3,
            )

            # Convert to DimensionScore objects
            dimensions = {
                "visual_impact": DimensionScore(
                    score=result.visual_impact.score,
                    analysis=result.visual_impact.analysis,
                ),
                "composition": DimensionScore(
                    score=result.composition.score,
                    analysis=result.composition.analysis,
                ),
                "color_harmony": DimensionScore(
                    score=result.color_harmony.score,
                    analysis=result.color_harmony.analysis,
                ),
                "text_clarity": DimensionScore(
                    score=result.text_clarity.score,
                    analysis=result.text_clarity.analysis,
                ),
            }

            # Calculate weighted total score
            total_score = self.calculate_weighted_score(dimensions)

            creative_score = CreativeScore(
                total_score=total_score,
                dimensions=dimensions,
                ai_analysis=result.overall_analysis,
            )

            log.info(
                "scoring_complete",
                total_score=total_score,
                visual_impact=result.visual_impact.score,
                composition=result.composition.score,
                color_harmony=result.color_harmony.score,
                text_clarity=result.text_clarity.score,
            )

            return creative_score

        except Exception as e:
            log.error("scoring_failed", error=str(e))
            raise

    def calculate_weighted_score(self, dimensions: dict[str, DimensionScore]) -> float:
        """Calculate weighted total score from dimension scores.

        Formula:
        total = visual_impact × 0.30 + composition × 0.25 +
                color_harmony × 0.25 + text_clarity × 0.20

        Args:
            dimensions: Dict of dimension name to DimensionScore

        Returns:
            Weighted total score (0-100), rounded to 1 decimal place
        """
        total = sum(
            dimensions[dim].score * weight
            for dim, weight in self.DIMENSION_WEIGHTS.items()
            if dim in dimensions
        )
        return round(total, 1)

    async def score_batch(self, image_urls: list[str]) -> list[CreativeScore]:
        """Score multiple creative images.

        Scores images sequentially to avoid rate limiting.

        Args:
            image_urls: List of image URLs to score

        Returns:
            List of CreativeScore results in same order as input
        """
        results = []
        for url in image_urls:
            score = await self.score(url)
            results.append(score)
        return results
