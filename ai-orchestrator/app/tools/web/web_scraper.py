"""Web Scraper Tool - Generic web page scraping.

This tool provides flexible web scraping capabilities:
- Simple HTTP requests for static pages
- Browser rendering for JavaScript-heavy pages
- LLM-powered intelligent extraction

Requirements: Architecture v2.0 - Web Scraping Enhancement
"""

import re
import time
from typing import Any, Literal

import aiohttp
import structlog
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field

from app.tools.base import (
    BaseTool,
    ToolCategory,
    ToolContext,
    ToolDefinition,
    ToolResult,
    ToolRiskLevel,
)

logger = structlog.get_logger(__name__)


class WebScrapeInput(BaseModel):
    """Input parameters for web_scrape tool."""

    url: str = Field(description="URL to scrape")
    method: Literal["simple", "browser"] = Field(
        default="simple",
        description="Scraping method: simple (HTTP) or browser (JavaScript rendering)",
    )
    selectors: dict[str, str] | None = Field(
        default=None,
        description="CSS selectors for structured extraction, e.g., {'title': 'h1', 'price': '.price'}",
    )
    wait_for: str | None = Field(
        default=None,
        description="CSS selector to wait for (browser mode only)",
    )
    extract_mode: Literal["structured", "text", "html", "llm"] = Field(
        default="text",
        description="Extraction mode: structured (CSS selectors), text (plain text), html (raw HTML), llm (AI extraction)",
    )
    llm_prompt: str | None = Field(
        default=None,
        description="Extraction prompt for LLM mode",
    )
    timeout: int = Field(default=30, ge=5, le=120, description="Request timeout in seconds")


class WebScrapeOutput(BaseModel):
    """Output from web_scrape tool."""

    success: bool
    url: str
    data: dict[str, Any] | None = None
    text: str | None = None
    html: str | None = None
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class WebScrapeTool(BaseTool[WebScrapeInput, WebScrapeOutput]):
    """Tool for scraping web pages.

    Supports multiple extraction methods:
    - Simple HTTP requests with aiohttp
    - Browser rendering with Playwright (for JS pages)
    - LLM-powered intelligent extraction
    """

    definition = ToolDefinition(
        name="web_scrape",
        description=(
            "抓取网页内容。支持简单HTTP请求（静态页面）和浏览器渲染（JavaScript动态页面）。"
            "可使用CSS选择器提取结构化数据，或使用AI智能提取关键信息。"
        ),
        category=ToolCategory.WEB,
        risk_level=ToolRiskLevel.LOW,
        credit_cost=0.5,
        requires_confirmation=False,
        parameters=WebScrapeInput.model_json_schema(),
        returns=WebScrapeOutput.model_json_schema(),
    )

    # User agent for requests
    USER_AGENT = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )

    def estimate_cost(self, params: WebScrapeInput) -> float:
        """Calculate cost based on method."""
        base_cost = self.definition.credit_cost
        # Browser rendering costs more
        if params.method == "browser":
            base_cost *= 2
        # LLM extraction costs more
        if params.extract_mode == "llm":
            base_cost += 1.0
        return base_cost

    async def execute(
        self, params: WebScrapeInput, context: ToolContext
    ) -> ToolResult:
        """Execute web scraping.

        Args:
            params: Scraping parameters
            context: Execution context

        Returns:
            ToolResult with scraped data or error
        """
        log = logger.bind(
            user_id=context.user_id,
            session_id=context.session_id,
            tool="web_scrape",
            url=params.url,
        )
        log.info("web_scrape_start", method=params.method, extract_mode=params.extract_mode)

        start_time = time.time()

        try:
            # Fetch HTML based on method
            if params.method == "simple":
                html = await self._simple_fetch(params.url, params.timeout)
            elif params.method == "browser":
                html = await self._browser_fetch(params.url, params.wait_for, params.timeout)
            else:
                return ToolResult.error_result(error=f"Unknown method: {params.method}")

            # Extract based on mode
            if params.extract_mode == "html":
                result = WebScrapeOutput(
                    success=True,
                    url=params.url,
                    html=html[:50000],  # Limit size
                    metadata={"length": len(html)},
                )

            elif params.extract_mode == "text":
                text = self._extract_text(html)
                result = WebScrapeOutput(
                    success=True,
                    url=params.url,
                    text=text[:20000],
                    metadata={"length": len(text)},
                )

            elif params.extract_mode == "structured" and params.selectors:
                data = self._extract_structured(html, params.selectors)
                result = WebScrapeOutput(
                    success=True,
                    url=params.url,
                    data=data,
                )

            elif params.extract_mode == "llm" and params.llm_prompt:
                data = await self._llm_extract(html, params.llm_prompt)
                result = WebScrapeOutput(
                    success=True,
                    url=params.url,
                    data=data,
                )

            else:
                return ToolResult.error_result(
                    error="Invalid extract_mode or missing required parameters (selectors for structured, llm_prompt for llm)"
                )

            execution_time = time.time() - start_time
            log.info("web_scrape_success", execution_time=execution_time)

            return ToolResult.success_result(
                data=result.model_dump(),
                credit_consumed=self.estimate_cost(params),
                execution_time=execution_time,
            )

        except aiohttp.ClientError as e:
            log.error("web_scrape_network_error", error=str(e))
            return ToolResult.error_result(error=f"网络请求失败: {str(e)}")
        except Exception as e:
            log.error("web_scrape_error", error=str(e), exc_info=True)
            return ToolResult.error_result(error=f"抓取失败: {str(e)}")

    async def _simple_fetch(self, url: str, timeout: int) -> str:
        """Simple HTTP request."""
        headers = {
            "User-Agent": self.USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
        }

        client_timeout = aiohttp.ClientTimeout(total=timeout)

        async with aiohttp.ClientSession(timeout=client_timeout) as session:
            async with session.get(url, headers=headers) as response:
                response.raise_for_status()
                return await response.text()

    async def _browser_fetch(
        self, url: str, wait_for: str | None, timeout: int
    ) -> str:
        """Browser rendering with Playwright."""
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            raise RuntimeError(
                "Playwright not installed. Run: pip install playwright && playwright install chromium"
            )

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            # Set user agent
            await page.set_extra_http_headers({"User-Agent": self.USER_AGENT})

            # Navigate
            await page.goto(url, wait_until="domcontentloaded", timeout=timeout * 1000)

            # Wait for specific element if requested
            if wait_for:
                try:
                    await page.wait_for_selector(wait_for, timeout=10000)
                except Exception:
                    pass  # Continue even if wait times out

            # Extra wait for dynamic content
            await page.wait_for_timeout(2000)

            # Get HTML
            html = await page.content()

            await browser.close()

            return html

    def _extract_text(self, html: str) -> str:
        """Extract plain text from HTML."""
        soup = BeautifulSoup(html, "html.parser")

        # Remove non-content elements
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()

        # Get text
        text = soup.get_text(separator="\n", strip=True)

        # Clean up whitespace
        text = re.sub(r"\n{3,}", "\n\n", text)

        return text

    def _extract_structured(self, html: str, selectors: dict[str, str]) -> dict[str, Any]:
        """Extract structured data using CSS selectors."""
        soup = BeautifulSoup(html, "html.parser")
        data = {}

        for key, selector in selectors.items():
            try:
                # Handle multiple elements
                elements = soup.select(selector)
                if len(elements) == 0:
                    data[key] = None
                elif len(elements) == 1:
                    data[key] = elements[0].get_text(strip=True)
                else:
                    data[key] = [el.get_text(strip=True) for el in elements]
            except Exception as e:
                data[key] = f"Error: {str(e)}"

        return data

    async def _llm_extract(self, html: str, prompt: str) -> dict[str, Any]:
        """Use LLM to intelligently extract data."""
        from app.services.gemini_client import GeminiClient

        # Clean HTML
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()
        clean_text = soup.get_text(separator="\n", strip=True)[:15000]

        gemini = GeminiClient()

        messages = [
            {
                "role": "system",
                "content": (
                    "你是一个网页数据提取专家。根据用户的指令从网页内容中提取结构化信息。"
                    "只返回JSON格式，不要有其他文字说明。"
                ),
            },
            {
                "role": "user",
                "content": f"""提取指令：{prompt}

网页内容：
{clean_text}

请返回JSON格式的提取结果。""",
            },
        ]

        result = await gemini.generate(messages, temperature=0.1)

        # Try to parse JSON
        import json

        try:
            # Find JSON in response
            json_match = result.find("{")
            json_end = result.rfind("}") + 1
            if json_match != -1 and json_end > json_match:
                return json.loads(result[json_match:json_end])
        except json.JSONDecodeError:
            pass

        # Return raw response if JSON parsing fails
        return {"raw_response": result}

    def validate_params(self, params: dict[str, Any]) -> WebScrapeInput:
        """Validate input parameters."""
        return WebScrapeInput(**params)
