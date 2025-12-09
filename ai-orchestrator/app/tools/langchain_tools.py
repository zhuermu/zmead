"""LangChain Tools integration.

This module provides wrappers for LangChain built-in tools to integrate
them with the unified tools architecture.
"""

import asyncio
import structlog
from typing import Any

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

                    # Extract search entry point if available
                    if hasattr(grounding_metadata, "search_entry_point"):
                        entry_point = grounding_metadata.search_entry_point
                        if hasattr(entry_point, "rendered_content"):
                            # This contains the rendered HTML with search results
                            pass

                    # Extract grounding chunks (source citations)
                    if hasattr(grounding_metadata, "grounding_chunks"):
                        for chunk in grounding_metadata.grounding_chunks:
                            if hasattr(chunk, "web") and chunk.web:
                                sources.append({
                                    "title": chunk.web.title if hasattr(chunk.web, "title") else "",
                                    "url": chunk.web.uri if hasattr(chunk.web, "uri") else "",
                                })

                    # Extract grounding supports (specific citations in text)
                    if hasattr(grounding_metadata, "grounding_supports"):
                        for support in grounding_metadata.grounding_supports:
                            if hasattr(support, "grounding_chunk_indices"):
                                # These are indices into grounding_chunks
                                pass

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
    """Wrapper for LangChain Calculator tool.

    This tool provides mathematical calculation capabilities.
    """

    def __init__(self):
        """Initialize the Calculator tool."""
        metadata = ToolMetadata(
            name="calculator",
            description=(
                "Perform mathematical calculations. "
                "Useful for computing metrics, ROI, percentages, "
                "and other numerical operations."
            ),
            category=ToolCategory.LANGCHAIN,
            parameters=[
                ToolParameter(
                    name="expression",
                    type="string",
                    description="Mathematical expression to evaluate",
                    required=True,
                ),
            ],
            returns="calculation result",
            credit_cost=0.0,
            tags=["calculator", "math", "computation", "langchain"],
        )

        super().__init__(metadata)

        # Lazy import to avoid dependency issues
        self._calculator_tool = None

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
            # Initialize calculator tool if needed
            if self._calculator_tool is None:
                try:
                    from langchain.chains import LLMMathChain
                    from langchain_google_genai import ChatGoogleGenerativeAI
                    from app.core.config import get_settings

                    settings = get_settings()
                    llm = ChatGoogleGenerativeAI(
                        model=settings.gemini_model_fast,
                        google_api_key=settings.gemini_api_key,
                        temperature=0,
                    )
                    self._calculator_tool = LLMMathChain.from_llm(llm)
                except ImportError:
                    raise ToolExecutionError(
                        message="Calculator tool not available. Install langchain.",
                        tool_name=self.name,
                        error_code="DEPENDENCY_MISSING",
                    )

            # Execute calculation
            result = await self._calculator_tool.arun(expression)

            log.info("calculator_complete", result=result)

            return {
                "success": True,
                "result": result,
                "expression": expression,
                "message": f"Calculated: {expression} = {result}",
            }

        except Exception as e:
            log.error("calculator_error", error=str(e), exc_info=True)
            raise ToolExecutionError(
                message=f"Calculation failed: {str(e)}",
                tool_name=self.name,
            )


class DateTimeTool(AgentTool):
    """Tool for date and time operations.

    This tool provides current date/time and date calculations.
    """

    def __init__(self):
        """Initialize the DateTime tool."""
        metadata = ToolMetadata(
            name="datetime",
            description=(
                "Get current date/time with weekday, or perform date calculations. "
                "Returns date AND weekday name. Use add_days to find future/past dates. "
                "Examples: 'today' returns '2025-12-03 (星期三)', "
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
            returns="date/time result with weekday name (e.g., '2025-12-04 (星期四)')",
            credit_cost=0.0,
            tags=["datetime", "date", "time", "weekday", "langchain"],
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
        from datetime import datetime, timedelta

        operation = parameters.get("operation", "now")

        log = logger.bind(tool=self.name, operation=operation)
        log.info("datetime_start")

        try:
            if operation == "now":
                now = datetime.now()
                weekday = self._get_weekday_name(now)
                result = now.isoformat()
                message = f"Current: {now.strftime('%Y-%m-%d %H:%M:%S')} ({weekday})"

            elif operation == "today":
                today = datetime.now()
                weekday = self._get_weekday_name(today)
                result = today.date().isoformat()
                message = f"Today: {result} ({weekday})"

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
                message = f"Difference: {diff} days"

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
                message = f"Result: {result} ({weekday})"

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


# Factory function to create all LangChain tools
def create_langchain_tools() -> list[AgentTool]:
    """Create all LangChain tools.

    Returns:
        List of LangChain tools
    """
    return [
        GoogleSearchTool(),
        CalculatorTool(),
        DateTimeTool(),
    ]
