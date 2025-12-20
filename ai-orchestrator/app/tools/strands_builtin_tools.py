"""Strands Built-in Tools - No LangChain Dependency.

This module provides essential built-in tools using pure Python and Gemini API:
- google_search: Web search using Gemini Grounding
- nova_search: Web search using Amazon Nova Grounding
- calculator: Math calculations using Python eval
- datetime: Date/time operations using Python datetime

These tools are lightweight and have no LangChain dependencies.
"""

import asyncio
import json
import re
import structlog
from datetime import datetime, timedelta
from typing import Any

import boto3
from google import genai
from google.genai import types

from app.core.config import get_settings
from app.tools.base import (
    AgentTool,
    ToolCategory,
    ToolExecutionError,
    ToolMetadata,
    ToolParameter,
)

logger = structlog.get_logger(__name__)


class GoogleSearchTool(AgentTool):
    """Google Search tool using Gemini Grounding with Google Search.

    This tool provides web search capabilities by leveraging Gemini's
    built-in Google Search grounding feature. It returns real-time
    search results with source citations.
    """

    def __init__(self):
        """Initialize the Google Search tool."""
        metadata = ToolMetadata(
            name="google_search",
            description=(
                "Search the web using Google Search. "
                "Returns real-time information from the web including "
                "current news, competitor data, market trends, product info, "
                "and general research. Results include source URLs."
            ),
            category=ToolCategory.LANGCHAIN,
            parameters=[
                ToolParameter(
                    name="query",
                    type="string",
                    description="Search query - be specific for better results",
                    required=True,
                ),
                ToolParameter(
                    name="language",
                    type="string",
                    description="Response language (e.g., 'zh' for Chinese, 'en' for English)",
                    required=False,
                    default="zh",
                ),
            ],
            returns="Search results with summaries and source URLs",
            credit_cost=1.0,
            tags=["search", "web", "research", "google", "grounding"],
        )

        super().__init__(metadata)

        # Lazy initialization of Gemini client
        self._client: genai.Client | None = None

    def _get_client(self) -> genai.Client:
        """Get or create Gemini client."""
        if self._client is None:
            settings = get_settings()
            self._client = genai.Client(api_key=settings.gemini_api_key)
        return self._client

    async def execute(
        self,
        parameters: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute Google search using Gemini Grounding.

        Args:
            parameters: Tool parameters
            context: Execution context

        Returns:
            Search results with summaries and sources

        Raises:
            ToolExecutionError: If search fails
        """
        query = parameters.get("query", "")
        language = parameters.get("language", "zh")

        log = logger.bind(tool=self.name, query=query, language=language)
        log.info("google_search_start")

        if not query:
            raise ToolExecutionError(
                message="Search query is required",
                tool_name=self.name,
                error_code="INVALID_PARAMS",
            )

        try:
            client = self._get_client()
            settings = get_settings()

            # Build prompt for search with language instruction
            lang_instruction = "请用中文回复" if language == "zh" else f"Please respond in {language}"
            search_prompt = f"""Search the web for: {query}

{lang_instruction}

Provide a comprehensive summary of the search results, including:
1. Key findings and facts
2. Important details and statistics
3. Source references

Format the response clearly with sections if needed."""

            # Use Gemini with Google Search grounding
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=settings.gemini_model_fast,
                contents=search_prompt,
                config=types.GenerateContentConfig(
                    tools=[types.Tool(google_search=types.GoogleSearch())],
                    temperature=0.2,
                ),
            )

            # Extract search results and grounding metadata
            result_text = response.text if response.text else ""

            # Extract grounding sources if available
            sources = []
            grounding_metadata = None

            if response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, "grounding_metadata") and candidate.grounding_metadata:
                    grounding_metadata = candidate.grounding_metadata

                    # Extract grounding chunks (source citations)
                    if hasattr(grounding_metadata, "grounding_chunks"):
                        for chunk in grounding_metadata.grounding_chunks:
                            if hasattr(chunk, "web") and chunk.web:
                                sources.append({
                                    "title": chunk.web.title if hasattr(chunk.web, "title") else "",
                                    "url": chunk.web.uri if hasattr(chunk.web, "uri") else "",
                                })

            log.info(
                "google_search_complete",
                result_length=len(result_text),
                sources_count=len(sources),
            )

            return {
                "success": True,
                "query": query,
                "summary": result_text,
                "sources": sources,
                "sources_count": len(sources),
                "message": f"搜索完成: {query}" if language == "zh" else f"Search completed: {query}",
            }

        except Exception as e:
            log.error("google_search_error", error=str(e), exc_info=True)
            raise ToolExecutionError(
                message=f"Search failed: {str(e)}",
                tool_name=self.name,
            )


class CalculatorTool(AgentTool):
    """Simple calculator tool using Python eval.

    This tool provides mathematical calculation capabilities without
    requiring LangChain or external dependencies.
    """

    def __init__(self):
        """Initialize the Calculator tool."""
        metadata = ToolMetadata(
            name="calculator",
            description=(
                "Perform mathematical calculations. "
                "Supports basic operations (+, -, *, /, **, %), "
                "functions (sqrt, sin, cos, log), and constants (pi, e). "
                "Useful for computing metrics, ROI, percentages."
            ),
            category=ToolCategory.LANGCHAIN,
            parameters=[
                ToolParameter(
                    name="expression",
                    type="string",
                    description="Mathematical expression to evaluate (e.g., '2 + 2', 'sqrt(16)', '100 * 0.15')",
                    required=True,
                ),
            ],
            returns="calculation result",
            credit_cost=0.0,
            tags=["calculator", "math", "computation"],
        )

        super().__init__(metadata)

    def _safe_eval(self, expression: str) -> float:
        """Safely evaluate mathematical expression.

        Args:
            expression: Mathematical expression

        Returns:
            Calculation result

        Raises:
            ValueError: If expression is invalid
        """
        import math

        # Remove whitespace
        expression = expression.strip()

        # Only allow safe characters
        allowed_chars = set("0123456789+-*/().%** ,")
        allowed_names = {"sqrt", "sin", "cos", "tan", "log", "log10", "exp", "pi", "e", "abs", "pow"}

        # Check for dangerous keywords
        dangerous = ["import", "exec", "eval", "compile", "__"]
        for word in dangerous:
            if word in expression.lower():
                raise ValueError(f"Dangerous keyword '{word}' not allowed")

        # Build safe namespace
        safe_dict = {
            "sqrt": math.sqrt,
            "sin": math.sin,
            "cos": math.cos,
            "tan": math.tan,
            "log": math.log,
            "log10": math.log10,
            "exp": math.exp,
            "abs": abs,
            "pow": pow,
            "pi": math.pi,
            "e": math.e,
            "__builtins__": {},
        }

        try:
            result = eval(expression, safe_dict, {})
            return float(result)
        except Exception as e:
            raise ValueError(f"Invalid expression: {str(e)}")

    async def execute(
        self,
        parameters: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute calculation.

        Args:
            parameters: Tool parameters
            context: Execution context

        Returns:
            Calculation result

        Raises:
            ToolExecutionError: If calculation fails
        """
        expression = parameters.get("expression", "")

        log = logger.bind(tool=self.name, expression=expression)
        log.info("calculator_start")

        if not expression:
            raise ToolExecutionError(
                message="Expression is required",
                tool_name=self.name,
                error_code="INVALID_PARAMS",
            )

        try:
            # Evaluate expression
            result = self._safe_eval(expression)

            log.info("calculator_complete", result=result)

            return {
                "success": True,
                "result": result,
                "expression": expression,
                "message": f"计算结果: {expression} = {result}",
            }

        except ValueError as e:
            log.warning("calculator_invalid_expression", error=str(e))
            raise ToolExecutionError(
                message=str(e),
                tool_name=self.name,
                error_code="INVALID_EXPRESSION",
            )

        except Exception as e:
            log.error("calculator_error", error=str(e), exc_info=True)
            raise ToolExecutionError(
                message=f"Calculation failed: {str(e)}",
                tool_name=self.name,
            )


class DateTimeTool(AgentTool):
    """Tool for date and time operations.

    This tool provides current date/time and date calculations.
    Pure Python implementation with no dependencies.
    """

    def __init__(self):
        """Initialize the DateTime tool."""
        metadata = ToolMetadata(
            name="datetime",
            description=(
                "Get current date/time with weekday, or perform date calculations. "
                "Returns date AND weekday name. Use add_days to find future/past dates. "
                "Examples: 'today' returns '2025-12-19 (星期四)', "
                "'add_days' with days=1 returns tomorrow's date and weekday."
            ),
            category=ToolCategory.LANGCHAIN,
            parameters=[
                ToolParameter(
                    name="operation",
                    type="string",
                    description="Operation: 'now' (current datetime), 'today' (date only), 'add_days' (calculate future/past date), 'date_diff' (days between dates)",
                    required=False,
                    default="now",
                    enum=["now", "today", "date_diff", "add_days"],
                ),
                ToolParameter(
                    name="date1",
                    type="string",
                    description="Base date for calculations (optional, defaults to today)",
                    required=False,
                ),
                ToolParameter(
                    name="date2",
                    type="string",
                    description="Second date (for date_diff)",
                    required=False,
                ),
                ToolParameter(
                    name="days",
                    type="number",
                    description="Number of days to add (positive for future, negative for past)",
                    required=False,
                ),
            ],
            returns="date/time result with weekday name (e.g., '2025-12-19 (星期四)')",
            credit_cost=0.0,
            tags=["datetime", "date", "time", "weekday"],
        )

        super().__init__(metadata)

    def _get_weekday_name(self, dt, chinese: bool = True) -> str:
        """Get weekday name from datetime."""
        weekdays_cn = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
        weekdays_en = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        weekday_idx = dt.weekday()
        return weekdays_cn[weekday_idx] if chinese else weekdays_en[weekday_idx]

    async def execute(
        self,
        parameters: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute datetime operation.

        Args:
            parameters: Tool parameters
            context: Execution context

        Returns:
            Date/time result

        Raises:
            ToolExecutionError: If operation fails
        """
        operation = parameters.get("operation", "now")

        log = logger.bind(tool=self.name, operation=operation)
        log.info("datetime_start")

        try:
            if operation == "now":
                now = datetime.now()
                weekday = self._get_weekday_name(now)
                result = now.isoformat()
                message = f"当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')} ({weekday})"

            elif operation == "today":
                today = datetime.now()
                weekday = self._get_weekday_name(today)
                result = today.date().isoformat()
                message = f"今天: {result} ({weekday})"

            elif operation == "date_diff":
                date1_str = parameters.get("date1")
                date2_str = parameters.get("date2")

                if not date1_str or not date2_str:
                    raise ToolExecutionError(
                        message="Both date1 and date2 are required for date_diff",
                        tool_name=self.name,
                        error_code="INVALID_PARAMS",
                    )

                date1 = datetime.fromisoformat(date1_str)
                date2 = datetime.fromisoformat(date2_str)
                diff = (date2 - date1).days

                result = diff
                message = f"日期差: {diff} 天"

            elif operation == "add_days":
                date1_str = parameters.get("date1")
                days = parameters.get("days", 0)

                # If no date1, use today as base
                if not date1_str:
                    date1 = datetime.now()
                else:
                    date1 = datetime.fromisoformat(date1_str)

                new_date = date1 + timedelta(days=days)
                weekday = self._get_weekday_name(new_date)
                result = new_date.date().isoformat()
                message = f"结果: {result} ({weekday})"

            else:
                raise ToolExecutionError(
                    message=f"Unknown operation: {operation}",
                    tool_name=self.name,
                    error_code="INVALID_OPERATION",
                )

            log.info("datetime_complete", result=result)

            return {
                "success": True,
                "result": result,
                "operation": operation,
                "message": message,
            }

        except ToolExecutionError:
            raise

        except Exception as e:
            log.error("datetime_error", error=str(e), exc_info=True)
            raise ToolExecutionError(
                message=f"DateTime operation failed: {str(e)}",
                tool_name=self.name,
            )


class NovaSearchTool(AgentTool):
    """Web search tool using Amazon Nova Grounding.

    This tool provides web search capabilities by leveraging Amazon Bedrock
    Nova's built-in grounding feature. It returns real-time search results
    with source citations.
    """

    def __init__(self):
        """Initialize the Nova Search tool."""
        metadata = ToolMetadata(
            name="nova_search",
            description=(
                "Search the web using Amazon Nova Grounding. "
                "Returns real-time information from the web including "
                "current news, competitor data, market trends, product info, "
                "and general research. Results include source URLs."
            ),
            category=ToolCategory.LANGCHAIN,
            parameters=[
                ToolParameter(
                    name="query",
                    type="string",
                    description="Search query - be specific for better results",
                    required=True,
                ),
                ToolParameter(
                    name="language",
                    type="string",
                    description="Response language (e.g., 'zh' for Chinese, 'en' for English)",
                    required=False,
                    default="zh",
                ),
            ],
            returns="Search results with summaries and source URLs",
            credit_cost=1.0,
            tags=["search", "web", "research", "nova", "grounding", "bedrock"],
        )

        super().__init__(metadata)

        # Lazy initialization of Bedrock client
        self._client = None

    def _get_client(self):
        """Get or create Bedrock client."""
        if self._client is None:
            settings = get_settings()
            self._client = boto3.client(
                service_name="bedrock-runtime",
                region_name=settings.bedrock_region,
            )
        return self._client

    async def execute(
        self,
        parameters: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute web search using Amazon Nova Grounding.

        Args:
            parameters: Tool parameters
            context: Execution context

        Returns:
            Search results with summaries and sources

        Raises:
            ToolExecutionError: If search fails
        """
        query = parameters.get("query", "")
        language = parameters.get("language", "zh")

        log = logger.bind(tool=self.name, query=query, language=language)
        log.info("nova_search_start")

        if not query:
            raise ToolExecutionError(
                message="Search query is required",
                tool_name=self.name,
                error_code="INVALID_PARAMS",
            )

        try:
            client = self._get_client()
            settings = get_settings()

            # Determine Nova model to use (prefer Nova Lite for faster search)
            nova_model = "us.amazon.nova-lite-v1:0"

            # Build prompt for search with language instruction
            lang_instruction = "请用中文回复" if language == "zh" else f"Please respond in {language}"
            search_prompt = f"""Search the web for: {query}

{lang_instruction}

Provide a comprehensive summary of the search results, including:
1. Key findings and facts
2. Important details and statistics
3. Source references

Format the response clearly with sections if needed."""

            # Use Bedrock Converse API with Nova Grounding
            log.info("calling_bedrock_converse", model=nova_model)

            # Note: Nova Grounding provides inline references in the text rather than structured citations
            # The references are embedded in the response text itself
            response = await asyncio.to_thread(
                client.converse,
                modelId=nova_model,
                messages=[
                    {
                        "role": "user",
                        "content": [{"text": search_prompt}],
                    }
                ],
                toolConfig={
                    "tools": [
                        {
                            "systemTool": {
                                "name": "nova_grounding",
                            }
                        }
                    ]
                },
                inferenceConfig={
                    "temperature": 0.2,
                    "maxTokens": 2048,
                },
            )

            log.info("bedrock_response_received", response_keys=list(response.keys()))

            # Extract text response
            result_text = ""
            sources = []

            # Parse response
            if "output" in response and "message" in response["output"]:
                message = response["output"]["message"]

                # Extract text content
                if "content" in message:
                    for content_block in message["content"]:
                        # Extract text
                        if "text" in content_block:
                            result_text += content_block["text"]

                        # Extract references/citations if they exist in content blocks
                        # (Future: if Nova adds structured citations)
                        if "reference" in content_block:
                            ref = content_block["reference"]
                            sources.append({
                                "title": ref.get("title", ""),
                                "url": ref.get("url", ref.get("uri", "")),
                            })

            # Note: Nova Grounding integrates source information inline in the generated text
            # rather than providing structured citations. The summary text already includes
            # references to sources where appropriate.

            log.info(
                "nova_search_complete",
                result_length=len(result_text),
                sources_count=len(sources),
            )

            return {
                "success": True,
                "query": query,
                "summary": result_text,
                "sources": sources,
                "sources_count": len(sources),
                "message": f"搜索完成: {query}" if language == "zh" else f"Search completed: {query}",
            }

        except Exception as e:
            log.error("nova_search_error", error=str(e), exc_info=True)
            raise ToolExecutionError(
                message=f"Search failed: {str(e)}",
                tool_name=self.name,
            )


class WebSearchTool(AgentTool):
    """Unified web search tool with automatic fallback.

    This tool provides web search with automatic provider fallback:
    1. First tries Amazon Nova Grounding (fast, AWS-native)
    2. Falls back to Google Search (Gemini Grounding) if Nova fails

    Users only see "web search" without knowing the underlying provider.
    """

    def __init__(self):
        """Initialize the unified Web Search tool."""
        metadata = ToolMetadata(
            name="web_search",
            description=(
                "Search the web for real-time information. "
                "Returns current news, competitor data, market trends, product info, "
                "and general research results. Automatically uses the best available search provider."
            ),
            category=ToolCategory.LANGCHAIN,
            parameters=[
                ToolParameter(
                    name="query",
                    type="string",
                    description="Search query - be specific for better results",
                    required=True,
                ),
                ToolParameter(
                    name="language",
                    type="string",
                    description="Response language (e.g., 'zh' for Chinese, 'en' for English)",
                    required=False,
                    default="zh",
                ),
            ],
            returns="Search results with summaries and source information",
            credit_cost=1.0,
            tags=["search", "web", "research", "internet"],
        )

        super().__init__(metadata)

        # Initialize both search providers
        self._nova_search = NovaSearchTool()
        self._google_search = GoogleSearchTool()

    async def execute(
        self,
        parameters: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute web search with automatic fallback.

        Args:
            parameters: Tool parameters
            context: Execution context

        Returns:
            Search results

        Raises:
            ToolExecutionError: If all search providers fail
        """
        query = parameters.get("query", "")
        language = parameters.get("language", "zh")

        log = logger.bind(tool=self.name, query=query, language=language)
        log.info("web_search_start")

        # Try Nova Search first (preferred for AWS-native integration)
        try:
            log.info("trying_nova_search")
            result = await self._nova_search.execute(parameters, context)
            log.info("web_search_complete", provider="nova", success=True)
            return {
                **result,
                "provider": "nova",  # Internal tracking only, not shown to user
            }
        except Exception as nova_error:
            log.warning(
                "nova_search_failed",
                error=str(nova_error),
                fallback="google_search",
            )

            # Fallback to Google Search
            try:
                log.info("trying_google_search_fallback")
                result = await self._google_search.execute(parameters, context)
                log.info("web_search_complete", provider="google", success=True)
                return {
                    **result,
                    "provider": "google",  # Internal tracking only
                }
            except Exception as google_error:
                log.error(
                    "all_search_providers_failed",
                    nova_error=str(nova_error),
                    google_error=str(google_error),
                )
                raise ToolExecutionError(
                    message=f"Web search failed: {str(google_error)}",
                    tool_name=self.name,
                )


# Factory function to create all Strands built-in tools
def create_strands_builtin_tools() -> list[AgentTool]:
    """Create all Strands built-in tools (no LangChain dependency).

    Returns:
        List of built-in tools:
        - web_search: Unified web search (Nova → Google fallback)
        - calculator: Math calculations using Python eval
        - datetime: Date/time operations
    """
    return [
        WebSearchTool(),
        CalculatorTool(),
        DateTimeTool(),
    ]
