"""LangChain Tools integration.

This module provides wrappers for LangChain built-in tools to integrate
them with the unified tools architecture.
"""

import structlog
from typing import Any

from app.tools.base import (
    AgentTool,
    ToolCategory,
    ToolExecutionError,
    ToolMetadata,
    ToolParameter,
)

logger = structlog.get_logger(__name__)


class GoogleSearchTool(AgentTool):
    """Wrapper for LangChain Google Search tool.

    This tool provides web search capabilities using Google Search API.
    """

    def __init__(self):
        """Initialize the Google Search tool."""
        metadata = ToolMetadata(
            name="google_search",
            description=(
                "Search the web using Google. "
                "Useful for finding current information, competitor data, "
                "market trends, and general research."
            ),
            category=ToolCategory.LANGCHAIN,
            parameters=[
                ToolParameter(
                    name="query",
                    type="string",
                    description="Search query",
                    required=True,
                ),
                ToolParameter(
                    name="num_results",
                    type="number",
                    description="Number of results to return (default 5)",
                    required=False,
                    default=5,
                ),
            ],
            returns="list of search results with titles, URLs, and snippets",
            credit_cost=0.5,
            tags=["search", "web", "research", "langchain"],
        )

        super().__init__(metadata)

        # Lazy import to avoid dependency issues
        self._search_tool = None

    async def execute(
        self,
        parameters: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute Google search.

        Args:
            parameters: Tool parameters
            context: Execution context

        Returns:
            Search results

        Raises:
            ToolExecutionError: If search fails
        """
        query = parameters.get("query", "")
        num_results = parameters.get("num_results", 5)

        log = logger.bind(tool=self.name, query=query, num_results=num_results)
        log.info("google_search_start")

        if not query:
            raise ToolExecutionError(
                message="Search query is required",
                tool_name=self.name,
                error_code="INVALID_PARAMS",
            )

        try:
            # Initialize search tool if needed
            if self._search_tool is None:
                try:
                    from langchain_community.tools import GoogleSearchRun
                    from langchain_community.utilities import GoogleSearchAPIWrapper

                    search = GoogleSearchAPIWrapper()
                    self._search_tool = GoogleSearchRun(api_wrapper=search)
                except ImportError:
                    raise ToolExecutionError(
                        message="Google Search tool not available. Install langchain-community.",
                        tool_name=self.name,
                        error_code="DEPENDENCY_MISSING",
                    )

            # Execute search
            results = await self._search_tool.arun(query)

            log.info("google_search_complete")

            return {
                "success": True,
                "results": results,
                "query": query,
                "message": f"Found search results for: {query}",
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
