"""
Competitor analyzer for Market Insights module.

Uses AI to analyze competitor product information, pricing strategy,
target audience, and generate competitive insights.

Requirements: 1.1, 1.2, 1.3, 1.4, 1.5
"""

import re
from typing import TYPE_CHECKING

import httpx
import structlog
from pydantic import BaseModel, Field

from ..models import (
    CompetitorAnalysis,
    CompetitorInfo,
    CompetitorInsights,
)

if TYPE_CHECKING:
    from app.services.gemini_client import GeminiClient
    from app.services.mcp_client import MCPClient

logger = structlog.get_logger(__name__)


class CompetitorAnalysisAIResult(BaseModel):
    """Structured output schema for Gemini competitor analysis."""

    name: str = Field(description="竞品名称")
    price: str = Field(description="价格（包含货币符号）")
    features: list[str] = Field(description="产品特点列表")
    target_audience: str = Field(description="目标受众描述")
    selling_points: list[str] = Field(description="产品卖点列表")
    pricing_strategy: str = Field(description="定价策略分析")
    marketing_approach: str = Field(description="营销方式分析")
    strengths: list[str] = Field(description="竞品优势列表")
    weaknesses: list[str] = Field(description="竞品劣势列表")
    recommendations: list[str] = Field(description="差异化竞争建议列表")


class CompetitorAnalyzerError(Exception):
    """Error raised during competitor analysis."""

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



class CompetitorAnalyzer:
    """Analyzes competitor products using AI.

    Extracts and analyzes:
    - Product information: name, price, features, target audience, selling points
    - Insights: pricing strategy, marketing approach, strengths, weaknesses
    - Recommendations: differentiation strategies

    Uses Gemini 2.5 Pro for comprehensive AI analysis with structured output.

    Requirements: 1.1, 1.2, 1.3, 1.4, 1.5
    """

    # Valid URL patterns for competitor analysis
    VALID_URL_PATTERNS = [
        r"^https?://",  # Must start with http:// or https://
    ]

    ANALYSIS_PROMPT = """你是一位专业的市场竞品分析师。请分析以下竞品页面，提供全面的竞品洞察。

**分析维度：**

1. **产品信息 (Product Information)**
   - 产品名称
   - 价格（包含货币符号，如 $29.99）
   - 产品特点（3-5个核心特点）
   - 目标受众（年龄、性别、兴趣等）
   - 产品卖点（3-5个核心卖点）

2. **竞品洞察 (Competitor Insights)**
   - 定价策略分析（高端/中端/低端，价值定位等）
   - 营销方式分析（社交媒体、KOL、广告投放等）
   - 竞品优势（3-5个）
   - 竞品劣势（3-5个）

3. **差异化建议 (Recommendations)**
   - 提供 3-5 条具体的差异化竞争建议
   - 建议应该可操作、具体、有针对性

**竞品页面 URL**: {competitor_url}

**页面内容摘要**:
{page_content}

请用中文回答，分析要具体、专业、有洞察力。如果某些信息无法从页面获取，请基于行业经验进行合理推断。"""

    def __init__(
        self,
        gemini_client: "GeminiClient | None" = None,
        mcp_client: "MCPClient | None" = None,
    ):
        """Initialize competitor analyzer.

        Args:
            gemini_client: Gemini client for AI analysis
            mcp_client: MCP client for data storage
        """
        self.gemini = gemini_client
        self.mcp = mcp_client
        self._log = logger.bind(component="competitor_analyzer")
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
        """Get or create HTTP client for fetching page content."""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0),
                follow_redirects=True,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5,zh-CN;q=0.3",
                },
            )
        return self._http_client

    def _is_valid_url(self, url: str) -> bool:
        """Check if URL is valid for analysis.

        Args:
            url: URL to validate

        Returns:
            True if URL is valid
        """
        if not url or not isinstance(url, str):
            return False

        for pattern in self.VALID_URL_PATTERNS:
            if re.search(pattern, url, re.IGNORECASE):
                return True
        return False

    def _extract_text_content(self, html: str) -> str:
        """Extract text content from HTML.

        Args:
            html: Raw HTML content

        Returns:
            Extracted text content (truncated to reasonable length)
        """
        # Remove script and style tags
        html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE)

        # Remove HTML tags
        text = re.sub(r"<[^>]+>", " ", html)

        # Clean up whitespace
        text = re.sub(r"\s+", " ", text).strip()

        # Truncate to reasonable length for AI analysis
        max_length = 8000
        if len(text) > max_length:
            text = text[:max_length] + "..."

        return text

    async def extract_product_info(self, competitor_url: str) -> str:
        """Extract product information from competitor URL.

        Fetches the competitor page and extracts relevant content.

        Args:
            competitor_url: Competitor product URL

        Returns:
            Extracted page content

        Raises:
            CompetitorAnalyzerError: If extraction fails
        """
        log = self._log.bind(competitor_url=competitor_url)
        log.info("extract_product_info_start")

        if not self._is_valid_url(competitor_url):
            raise CompetitorAnalyzerError(
                f"Invalid URL format: {competitor_url}",
                code="INVALID_URL",
                retryable=False,
            )

        try:
            client = await self._get_http_client()
            response = await client.get(competitor_url)
            response.raise_for_status()

            html = response.text
            content = self._extract_text_content(html)

            log.info("extract_product_info_success", content_length=len(content))
            return content

        except httpx.HTTPStatusError as e:
            log.error("extract_product_info_http_error", status=e.response.status_code)
            raise CompetitorAnalyzerError(
                f"Failed to fetch competitor page: HTTP {e.response.status_code}",
                code="HTTP_ERROR",
                retryable=e.response.status_code >= 500,
            )

        except httpx.TimeoutException:
            log.error("extract_product_info_timeout")
            raise CompetitorAnalyzerError(
                "Timeout while fetching competitor page",
                code="TIMEOUT",
                retryable=True,
            )

        except Exception as e:
            log.error("extract_product_info_error", error=str(e))
            raise CompetitorAnalyzerError(
                f"Failed to extract product info: {e}",
                code="EXTRACTION_ERROR",
                retryable=False,
            )

    async def generate_insights(
        self,
        competitor_url: str,
        page_content: str,
    ) -> CompetitorAnalysisAIResult:
        """Generate insights using AI analysis.

        Args:
            competitor_url: Competitor URL
            page_content: Extracted page content

        Returns:
            AI-generated analysis result

        Raises:
            CompetitorAnalyzerError: If AI analysis fails
        """
        log = self._log.bind(competitor_url=competitor_url)
        log.info("generate_insights_start")

        gemini = self._get_gemini_client()

        prompt = self.ANALYSIS_PROMPT.format(
            competitor_url=competitor_url,
            page_content=page_content if page_content else "无法获取页面内容，请基于URL进行分析",
        )

        messages = [
            {
                "role": "user",
                "content": prompt,
            }
        ]

        try:
            result: CompetitorAnalysisAIResult = await gemini.structured_output(
                messages=messages,
                schema=CompetitorAnalysisAIResult,
                temperature=0.2,
            )

            log.info(
                "generate_insights_success",
                features_count=len(result.features),
                recommendations_count=len(result.recommendations),
            )

            return result

        except Exception as e:
            log.error("generate_insights_failed", error=str(e))
            raise CompetitorAnalyzerError(
                f"AI analysis failed: {e}",
                code="AI_ERROR",
                retryable=True,
            )


    async def analyze(
        self,
        competitor_url: str,
        analysis_type: str = "product",
        depth: str = "detailed",
    ) -> CompetitorAnalysis:
        """Analyze competitor product.

        Extracts product information and uses AI to generate comprehensive
        competitive insights.

        Args:
            competitor_url: Competitor product URL
            analysis_type: Type of analysis ("product" default)
            depth: Analysis depth ("detailed" default)

        Returns:
            CompetitorAnalysis with complete insights

        Raises:
            CompetitorAnalyzerError: If analysis fails

        Requirements: 1.1, 1.2, 1.3, 1.4, 1.5
        """
        log = self._log.bind(
            competitor_url=competitor_url,
            analysis_type=analysis_type,
            depth=depth,
        )
        log.info("analyze_start")

        try:
            # Extract product information from page
            page_content = await self.extract_product_info(competitor_url)

            # Generate AI insights
            ai_result = await self.generate_insights(competitor_url, page_content)

            # Build response models
            competitor_info = CompetitorInfo(
                name=ai_result.name,
                price=ai_result.price,
                features=ai_result.features,
                target_audience=ai_result.target_audience,
                selling_points=ai_result.selling_points,
            )

            insights = CompetitorInsights(
                pricing_strategy=ai_result.pricing_strategy,
                marketing_approach=ai_result.marketing_approach,
                strengths=ai_result.strengths,
                weaknesses=ai_result.weaknesses,
            )

            analysis = CompetitorAnalysis(
                status="success",
                competitor_info=competitor_info,
                insights=insights,
                recommendations=ai_result.recommendations,
            )

            log.info(
                "analyze_complete",
                competitor_name=ai_result.name,
                recommendations_count=len(ai_result.recommendations),
            )

            return analysis

        except CompetitorAnalyzerError as e:
            log.error("analyze_failed", error=str(e), code=e.code)
            return CompetitorAnalysis(
                status="error",
                competitor_info=None,
                insights=None,
                recommendations=[],
                error_code=e.code or "ANALYSIS_ERROR",
                message=e.message,
            )

        except Exception as e:
            log.error("analyze_unexpected_error", error=str(e))
            return CompetitorAnalysis(
                status="error",
                competitor_info=None,
                insights=None,
                recommendations=[],
                error_code="UNEXPECTED_ERROR",
                message=f"Unexpected error during analysis: {e}",
            )

    async def save_analysis(
        self,
        user_id: str,
        competitor_url: str,
        analysis: CompetitorAnalysis,
    ) -> dict:
        """Save analysis result to Web Platform via MCP.

        Args:
            user_id: User ID
            competitor_url: Competitor URL
            analysis: Analysis result to save

        Returns:
            Save result from MCP

        Raises:
            Exception: If save fails
        """
        log = self._log.bind(user_id=user_id, competitor_url=competitor_url)
        log.info("save_analysis_start")

        if analysis.status != "success" or analysis.competitor_info is None:
            log.warning("save_analysis_skipped_error_result")
            return {"saved": False, "reason": "Analysis was not successful"}

        mcp = self._get_mcp_client()

        try:
            result = await mcp.call_tool(
                "save_insight",
                {
                    "user_id": user_id,
                    "insight_type": "competitor_analysis",
                    "data": {
                        "competitor_url": competitor_url,
                        "competitor_info": analysis.competitor_info.model_dump(),
                        "insights": analysis.insights.model_dump() if analysis.insights else None,
                        "recommendations": analysis.recommendations,
                    },
                },
            )

            log.info("save_analysis_complete")
            return result

        except Exception as e:
            log.error("save_analysis_failed", error=str(e))
            raise

    async def analyze_and_save(
        self,
        user_id: str,
        competitor_url: str,
        analysis_type: str = "product",
        depth: str = "detailed",
    ) -> CompetitorAnalysis:
        """Analyze competitor and save results.

        Convenience method that combines analyze() and save_analysis().

        Args:
            user_id: User ID
            competitor_url: Competitor URL
            analysis_type: Type of analysis
            depth: Analysis depth

        Returns:
            CompetitorAnalysis result
        """
        log = self._log.bind(user_id=user_id, competitor_url=competitor_url)
        log.info("analyze_and_save_start")

        # Analyze the competitor
        analysis = await self.analyze(competitor_url, analysis_type, depth)

        # Save if successful
        if analysis.status == "success":
            try:
                await self.save_analysis(user_id, competitor_url, analysis)
            except Exception as e:
                log.warning("save_failed_but_analysis_complete", error=str(e))

        log.info("analyze_and_save_complete")
        return analysis

    async def close(self) -> None:
        """Close HTTP client."""
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()
            self._http_client = None
