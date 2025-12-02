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
                "Get current date and time, or perform date calculations. "
                "Useful for time-based queries, scheduling, and date arithmetic."
            ),
            category=ToolCategory.LANGCHAIN,
            parameters=[
                ToolParameter(
                    name="operation",
                    type="string",
                    description="Operation to perform",
                    required=False,
                    default="now",
                    enum=["now", "today", "date_diff", "add_days"],
                ),
                ToolParameter(
                    name="date1",
                    type="string",
                    description="First date (for date_diff, add_days)",
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
                    description="Number of days (for add_days)",
                    required=False,
                ),
            ],
            returns="date/time result",
            credit_cost=0.0,
            tags=["datetime", "date", "time", "langchain"],
        )

        super().__init__(metadata)

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
                result = datetime.now().isoformat()
                message = f"Current date and time: {result}"

            elif operation == "today":
                result = datetime.now().date().isoformat()
                message = f"Today's date: {result}"

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

                if not date1_str:
                    raise ToolExecutionError(
                        message="date1 is required for add_days",
                        tool_name=self.name,
                        error_code="INVALID_PARAMS",
                    )

                date1 = datetime.fromisoformat(date1_str)
                new_date = date1 + timedelta(days=days)
                result = new_date.isoformat()
                message = f"Result: {result}"

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
