"""
Competitor creative analyzer.

Requirements: 3.1, 3.2, 3.3, 3.5

This module implements competitor ad creative analysis from TikTok,
using Gemini 2.5 Flash for AI-powered analysis of:
- Composition
- Color scheme
- Selling points
- Copy structure
"""

import re
from datetime import datetime
from typing import TYPE_CHECKING

import httpx
import structlog
from pydantic import BaseModel, Field

from ..models import CompetitorAnalysis
from ..utils.retry import retry_mcp_call

if TYPE_CHECKING:
    from app.services.gemini_client import GeminiClient
    from app.services.mcp_client import MCPClient

logger = structlog.get_logger(__name__)


class CompetitorAnalysisResult(BaseModel):
    """Structured output schema for Gemini competitor analysis."""

    composition: str = Field(
        description="构图分析：描述画面布局、主体位置、视觉层次等"
    )
    color_scheme: str = Field(
        description="色彩方案：描述主色调、配色风格、色彩情感等"
    )
    selling_points: list[str] = Field(
        description="卖点列表：提取广告中展示的产品/服务卖点"
    )
    copy_structure: str = Field(
        description="文案结构：分析文案的组织方式、标题、正文、CTA等"
    )
    recommendations: list[str] = Field(
        description="建议：基于分析给出的创意优化建议"
    )


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
    """Analyzes competitor ad creatives from TikTok.

    Extracts and analyzes:
    - Composition: Layout, visual hierarchy, focal points
    - Color scheme: Primary colors, palette style, emotional impact
    - Selling points: Key product/service benefits highlighted
    - Copy structure: Headline, body, CTA organization

    Uses Gemini 2.5 Flash for fast AI analysis with structured output.

    Requirements: 3.1, 3.2, 3.3, 3.5
    """

    # TikTok ad URL patterns
    TIKTOK_AD_PATTERNS = [
        r"tiktok\.com/.*",
        r"vm\.tiktok\.com/.*",
        r"vt\.tiktok\.com/.*",
    ]

    ANALYSIS_PROMPT = """你是一位专业的广告创意分析师。请分析这个广告素材，从以下几个维度进行深入分析：

1. **构图分析 (Composition)**
   - 画面布局方式（居中、三分法、对角线等）
   - 主体位置和视觉焦点
   - 视觉层次和引导线
   - 空间利用和留白

2. **色彩方案 (Color Scheme)**
   - 主色调和辅助色
   - 配色风格（暖色、冷色、对比色等）
   - 色彩传达的情感和品牌调性
   - 色彩对比度和可读性

3. **卖点提取 (Selling Points)**
   - 产品/服务的核心卖点
   - 差异化优势
   - 用户痛点解决方案
   - 价值主张

4. **文案结构 (Copy Structure)**
   - 标题/Hook 的写法
   - 正文内容组织
   - CTA（行动号召）设计
   - 文案与画面的配合

5. **优化建议 (Recommendations)**
   - 基于分析给出 3-5 条具体的创意优化建议
   - 建议应该可操作、具体

广告素材 URL: {image_url}

请用中文回答，分析要具体、专业、有洞察力。"""

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

        Raises:
            ValueError: If no client available and cannot create one
        """
        if self.gemini is not None:
            return self.gemini

        # Lazy import to avoid circular dependencies
        from app.services.gemini_client import GeminiClient

        self.gemini = GeminiClient()
        return self.gemini

    def _get_mcp_client(self) -> "MCPClient":
        """Get or create MCP client.

        Returns:
            MCPClient instance

        Raises:
            ValueError: If no client available and cannot create one
        """
        if self.mcp is not None:
            return self.mcp

        # Lazy import to avoid circular dependencies
        from app.services.mcp_client import MCPClient

        self.mcp = MCPClient()
        return self.mcp

    async def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client for fetching ad content."""
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
                },
            )
        return self._http_client

    def _is_valid_tiktok_url(self, url: str) -> bool:
        """Check if URL is a valid TikTok ad URL.

        Args:
            url: URL to validate

        Returns:
            True if URL matches TikTok patterns
        """
        for pattern in self.TIKTOK_AD_PATTERNS:
            if re.search(pattern, url, re.IGNORECASE):
                return True
        return False

    async def extract_creative(self, ad_url: str) -> str:
        """Extract creative image/video URL from TikTok ad URL.

        Fetches the TikTok ad page and extracts the media URL.
        For MVP, we support image extraction. Video extraction
        will be added in a future version.

        Args:
            ad_url: TikTok ad URL

        Returns:
            Extracted media URL (image or video thumbnail)

        Raises:
            CompetitorAnalyzerError: If extraction fails
        """
        log = self._log.bind(ad_url=ad_url)
        log.info("extract_creative_start")

        if not self._is_valid_tiktok_url(ad_url):
            raise CompetitorAnalyzerError(
                f"Invalid TikTok URL: {ad_url}",
                code="INVALID_URL",
                retryable=False,
            )

        try:
            client = await self._get_http_client()
            response = await client.get(ad_url)
            response.raise_for_status()

            html = response.text

            # Try to extract image URL from meta tags
            # TikTok uses og:image for preview images
            og_image_match = re.search(
                r'<meta[^>]*property=["\']og:image["\'][^>]*content=["\']([^"\']+)["\']',
                html,
                re.IGNORECASE,
            )

            if og_image_match:
                image_url = og_image_match.group(1)
                log.info("extract_creative_success", image_url=image_url)
                return image_url

            # Try alternative pattern
            og_image_match = re.search(
                r'<meta[^>]*content=["\']([^"\']+)["\'][^>]*property=["\']og:image["\']',
                html,
                re.IGNORECASE,
            )

            if og_image_match:
                image_url = og_image_match.group(1)
                log.info("extract_creative_success", image_url=image_url)
                return image_url

            # Try to find video thumbnail
            thumbnail_match = re.search(
                r'"thumbnailUrl":\s*"([^"]+)"',
                html,
            )

            if thumbnail_match:
                image_url = thumbnail_match.group(1).replace("\\u002F", "/")
                log.info("extract_creative_success", image_url=image_url)
                return image_url

            # If no image found, use the original URL for analysis
            # The AI model can still analyze the page content
            log.warning("no_image_found_using_original_url")
            return ad_url

        except httpx.HTTPStatusError as e:
            log.error("extract_creative_http_error", status=e.response.status_code)
            raise CompetitorAnalyzerError(
                f"Failed to fetch TikTok ad: HTTP {e.response.status_code}",
                code="HTTP_ERROR",
                retryable=e.response.status_code >= 500,
            )

        except httpx.TimeoutException:
            log.error("extract_creative_timeout")
            raise CompetitorAnalyzerError(
                "Timeout while fetching TikTok ad",
                code="TIMEOUT",
                retryable=True,
            )

        except Exception as e:
            log.error("extract_creative_error", error=str(e))
            raise CompetitorAnalyzerError(
                f"Failed to extract creative: {e}",
                code="EXTRACTION_ERROR",
                retryable=False,
            )

    async def analyze(self, ad_url: str) -> CompetitorAnalysis:
        """Analyze competitor ad creative.

        Extracts the creative from the ad URL and uses Gemini 2.5 Flash
        to analyze composition, color scheme, selling points, and copy structure.

        Args:
            ad_url: TikTok ad URL

        Returns:
            CompetitorAnalysis with detailed insights

        Raises:
            CompetitorAnalyzerError: If analysis fails
            GeminiError: If AI analysis fails
        """
        log = self._log.bind(ad_url=ad_url)
        log.info("analyze_start")

        # Extract creative URL from ad page
        image_url = await self.extract_creative(ad_url)

        gemini = self._get_gemini_client()

        # Build the prompt with image URL
        prompt = self.ANALYSIS_PROMPT.format(image_url=image_url)

        messages = [
            {
                "role": "user",
                "content": prompt,
            }
        ]

        try:
            result: CompetitorAnalysisResult = await gemini.fast_structured_output(
                messages=messages,
                schema=CompetitorAnalysisResult,
                temperature=0.3,
            )

            analysis = CompetitorAnalysis(
                composition=result.composition,
                color_scheme=result.color_scheme,
                selling_points=result.selling_points,
                copy_structure=result.copy_structure,
                recommendations=result.recommendations,
                saved_at=None,  # Not saved yet
            )

            log.info(
                "analyze_complete",
                selling_points_count=len(result.selling_points),
                recommendations_count=len(result.recommendations),
            )

            return analysis

        except Exception as e:
            log.error("analyze_failed", error=str(e))
            raise

    async def save_analysis(
        self,
        user_id: str,
        ad_url: str,
        analysis: CompetitorAnalysis,
    ) -> CompetitorAnalysis:
        """Save analysis result to Web Platform via MCP.

        Args:
            user_id: User ID
            ad_url: Original ad URL
            analysis: Analysis result to save

        Returns:
            Updated CompetitorAnalysis with saved_at timestamp

        Raises:
            MCPError: If save fails
        """
        log = self._log.bind(user_id=user_id, ad_url=ad_url)
        log.info("save_analysis_start")

        mcp = self._get_mcp_client()

        async def _save():
            return await mcp.call_tool(
                "save_competitor_analysis",
                {
                    "ad_url": ad_url,
                    "composition": analysis.composition,
                    "color_scheme": analysis.color_scheme,
                    "selling_points": analysis.selling_points,
                    "copy_structure": analysis.copy_structure,
                    "recommendations": analysis.recommendations,
                },
            )

        try:
            result = await retry_mcp_call(_save, context="save_competitor_analysis")

            saved_at = result.get("saved_at", datetime.utcnow().isoformat())

            log.info("save_analysis_complete", saved_at=saved_at)

            # Return updated analysis with saved_at
            return CompetitorAnalysis(
                composition=analysis.composition,
                color_scheme=analysis.color_scheme,
                selling_points=analysis.selling_points,
                copy_structure=analysis.copy_structure,
                recommendations=analysis.recommendations,
                saved_at=saved_at,
            )

        except Exception as e:
            log.error("save_analysis_failed", error=str(e))
            raise

    async def analyze_and_save(
        self,
        user_id: str,
        ad_url: str,
    ) -> CompetitorAnalysis:
        """Analyze competitor ad and save results.

        Convenience method that combines analyze() and save_analysis().

        Args:
            user_id: User ID
            ad_url: TikTok ad URL

        Returns:
            CompetitorAnalysis with saved_at timestamp

        Raises:
            CompetitorAnalyzerError: If analysis fails
            MCPError: If save fails
        """
        log = self._log.bind(user_id=user_id, ad_url=ad_url)
        log.info("analyze_and_save_start")

        # Analyze the ad
        analysis = await self.analyze(ad_url)

        # Save the results
        saved_analysis = await self.save_analysis(user_id, ad_url, analysis)

        log.info("analyze_and_save_complete")

        return saved_analysis

    async def close(self) -> None:
        """Close HTTP client."""
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()
            self._http_client = None
