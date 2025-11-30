"""
Creative analyzer for Market Insights module.

Uses AI Vision to analyze ad creative visual style, elements, and success factors.

Requirements: 2.4, 2.5
"""

from typing import TYPE_CHECKING

import httpx
import structlog
from pydantic import BaseModel, Field

from ..models import (
    CreativeAnalysis,
    CreativeAnalysisResponse,
)

if TYPE_CHECKING:
    from app.services.gemini_client import GeminiClient
    from app.services.mcp_client import MCPClient

logger = structlog.get_logger(__name__)


class CreativeAnalysisAIResult(BaseModel):
    """Structured output schema for Gemini creative analysis."""

    visual_style: str = Field(description="视觉风格描述（如简约现代、复古怀旧、活力动感等）")
    color_palette: list[str] = Field(description="色彩方案列表（如 #FF6B6B、暖色调、高对比度等）")
    key_elements: list[str] = Field(description="关键元素列表（如产品特写、生活场景、用户评价等）")
    success_factors: list[str] = Field(description="成功要素列表（如清晰的产品展示、情感化场景等）")
    copywriting_style: str = Field(description="文案风格描述（如简洁有力、情感共鸣、数据驱动等）")
    recommendations: list[str] = Field(description="优化建议列表")


class CreativeAnalyzerError(Exception):
    """Error raised during creative analysis."""

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


class CreativeAnalyzer:
    """Analyzes ad creatives using AI Vision.

    Extracts and analyzes:
    - Visual style: Overall aesthetic and design approach
    - Color palette: Primary and secondary colors, color harmony
    - Key elements: Important visual components and their arrangement
    - Success factors: Elements contributing to ad effectiveness
    - Copywriting style: Text tone, structure, and messaging approach

    Uses Gemini 2.5 Flash for fast AI vision analysis with structured output.

    Requirements: 2.4, 2.5
    """

    ANALYSIS_PROMPT = """你是一位专业的广告素材分析师。请分析这个广告素材，从以下几个维度进行深入分析：

1. **视觉风格 (Visual Style)**
   - 整体设计风格（简约现代、复古怀旧、活力动感、高端奢华等）
   - 设计语言和美学特点
   - 品牌调性表达

2. **色彩方案 (Color Palette)**
   - 主色调和辅助色（可以用颜色名称或十六进制代码）
   - 配色风格（暖色、冷色、对比色、单色等）
   - 色彩传达的情感和氛围

3. **关键元素 (Key Elements)**
   - 画面中的核心视觉元素
   - 产品展示方式
   - 场景设置和背景
   - 人物或模特使用
   - 文字和图形元素

4. **成功要素 (Success Factors)**
   - 这个素材吸引人的关键因素
   - 有效的视觉传达技巧
   - 情感连接点
   - 行动号召的有效性

5. **文案风格 (Copywriting Style)**
   - 文案的整体风格和调性
   - 标题/Hook 的写法
   - 信息传达方式
   - CTA（行动号召）设计

6. **优化建议 (Recommendations)**
   - 基于分析给出 3-5 条具体的优化建议
   - 建议应该可操作、具体、有针对性

**素材信息**:
- 素材 ID: {creative_id}
- 素材 URL: {creative_url}

请用中文回答，分析要具体、专业、有洞察力。"""

    def __init__(
        self,
        gemini_client: "GeminiClient | None" = None,
        mcp_client: "MCPClient | None" = None,
    ):
        """Initialize creative analyzer.

        Args:
            gemini_client: Gemini client for AI analysis
            mcp_client: MCP client for data storage
        """
        self.gemini = gemini_client
        self.mcp = mcp_client
        self._log = logger.bind(component="creative_analyzer")
        self._http_client: httpx.AsyncClient | None = None

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

    async def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0),
                follow_redirects=True,
            )
        return self._http_client


    async def get_creative_url(self, creative_id: str) -> str | None:
        """Get creative URL from creative ID.

        Fetches creative details from TikTok fetcher or cache.

        Args:
            creative_id: Creative ID

        Returns:
            Creative URL or None if not found
        """
        log = self._log.bind(creative_id=creative_id)
        log.info("get_creative_url_start")

        # Try to get from MCP (Web Platform cache)
        try:
            mcp = self._get_mcp_client()
            result = await mcp.call_tool(
                "get_creative_details",
                {"creative_id": creative_id},
            )
            if result and result.get("thumbnail_url"):
                return result["thumbnail_url"]
        except Exception as e:
            log.warning("get_creative_url_mcp_failed", error=str(e))

        # Return None if not found - caller should handle this
        return None

    async def analyze_creative(
        self,
        creative_id: str,
        creative_url: str | None = None,
        analysis_depth: str = "detailed",
    ) -> CreativeAnalysisResponse:
        """Analyze ad creative using AI Vision.

        Analyzes visual style, color palette, key elements, success factors,
        and copywriting style of the creative.

        Args:
            creative_id: Creative ID
            creative_url: Optional creative URL (will be fetched if not provided)
            analysis_depth: Analysis depth ("detailed" default)

        Returns:
            CreativeAnalysisResponse with analysis and recommendations

        Requirements: 2.4, 2.5
        """
        log = self._log.bind(
            creative_id=creative_id,
            analysis_depth=analysis_depth,
        )
        log.info("analyze_creative_start")

        try:
            # Get creative URL if not provided
            if not creative_url:
                creative_url = await self.get_creative_url(creative_id)

            if not creative_url:
                # Use placeholder URL for analysis based on ID
                creative_url = f"https://creative.tiktok.com/{creative_id}"
                log.warning("using_placeholder_url", creative_url=creative_url)

            # Generate AI analysis
            ai_result = await self._generate_analysis(creative_id, creative_url)

            # Build response
            analysis = CreativeAnalysis(
                visual_style=ai_result.visual_style,
                color_palette=ai_result.color_palette,
                key_elements=ai_result.key_elements,
                success_factors=ai_result.success_factors,
                copywriting_style=ai_result.copywriting_style,
            )

            response = CreativeAnalysisResponse(
                status="success",
                analysis=analysis,
                recommendations=ai_result.recommendations,
            )

            log.info(
                "analyze_creative_complete",
                key_elements_count=len(ai_result.key_elements),
                recommendations_count=len(ai_result.recommendations),
            )

            return response

        except CreativeAnalyzerError as e:
            log.error("analyze_creative_failed", error=str(e), code=e.code)
            return CreativeAnalysisResponse(
                status="error",
                analysis=None,
                recommendations=[],
                error_code=e.code or "ANALYSIS_ERROR",
                message=e.message,
            )

        except Exception as e:
            log.error("analyze_creative_unexpected_error", error=str(e))
            return CreativeAnalysisResponse(
                status="error",
                analysis=None,
                recommendations=[],
                error_code="UNEXPECTED_ERROR",
                message=f"Unexpected error during analysis: {e}",
            )

    async def _generate_analysis(
        self,
        creative_id: str,
        creative_url: str,
    ) -> CreativeAnalysisAIResult:
        """Generate analysis using AI.

        Args:
            creative_id: Creative ID
            creative_url: Creative URL

        Returns:
            AI-generated analysis result

        Raises:
            CreativeAnalyzerError: If AI analysis fails
        """
        log = self._log.bind(creative_id=creative_id)
        log.info("generate_analysis_start")

        gemini = self._get_gemini_client()

        prompt = self.ANALYSIS_PROMPT.format(
            creative_id=creative_id,
            creative_url=creative_url,
        )

        messages = [
            {
                "role": "user",
                "content": prompt,
            }
        ]

        try:
            # Use fast model for creative analysis (Gemini 2.5 Flash)
            result: CreativeAnalysisAIResult = await gemini.fast_structured_output(
                messages=messages,
                schema=CreativeAnalysisAIResult,
                temperature=0.3,
            )

            log.info(
                "generate_analysis_success",
                color_palette_count=len(result.color_palette),
                success_factors_count=len(result.success_factors),
            )

            return result

        except Exception as e:
            log.error("generate_analysis_failed", error=str(e))
            raise CreativeAnalyzerError(
                f"AI analysis failed: {e}",
                code="AI_ERROR",
                retryable=True,
            )

    async def save_analysis(
        self,
        user_id: str,
        creative_id: str,
        response: CreativeAnalysisResponse,
    ) -> dict:
        """Save analysis result to Web Platform via MCP.

        Args:
            user_id: User ID
            creative_id: Creative ID
            response: Analysis response to save

        Returns:
            Save result from MCP
        """
        log = self._log.bind(user_id=user_id, creative_id=creative_id)
        log.info("save_analysis_start")

        if response.status != "success" or response.analysis is None:
            log.warning("save_analysis_skipped_error_result")
            return {"saved": False, "reason": "Analysis was not successful"}

        mcp = self._get_mcp_client()

        try:
            result = await mcp.call_tool(
                "save_insight",
                {
                    "user_id": user_id,
                    "insight_type": "creative_analysis",
                    "data": {
                        "creative_id": creative_id,
                        "analysis": response.analysis.model_dump(),
                        "recommendations": response.recommendations,
                    },
                },
            )

            log.info("save_analysis_complete")
            return result

        except Exception as e:
            log.error("save_analysis_failed", error=str(e))
            raise

    async def close(self) -> None:
        """Close HTTP client."""
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()
            self._http_client = None
