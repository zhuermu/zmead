"""Performance Tools for ad performance analysis.

This module provides Agent Custom Tools for performance-related operations:
- analyze_performance_tool: AI-powered performance analysis using Gemini
- detect_anomaly_tool: Detect performance anomalies using Gemini
- generate_recommendations_tool: Generate optimization recommendations using Gemini

These tools can call LLMs (Gemini) for AI capabilities.
They call the module functions directly (not through capability.py).
"""

import structlog
from typing import Any

from app.services.gemini_client import GeminiClient, GeminiError
from app.tools.base import (
    AgentTool,
    ToolCategory,
    ToolExecutionError,
    ToolMetadata,
    ToolParameter,
)

logger = structlog.get_logger(__name__)


class AnalyzePerformanceTool(AgentTool):
    """Tool for AI-powered performance analysis using Gemini.

    This tool analyzes advertising performance data and provides
    insights on trends, patterns, and optimization opportunities.
    """

    def __init__(self, gemini_client: GeminiClient | None = None):
        """Initialize the analyze performance tool.

        Args:
            gemini_client: Gemini client for analysis
        """
        metadata = ToolMetadata(
            name="analyze_performance_tool",
            description=(
                "Analyze advertising performance data using AI. "
                "Provides insights on trends, patterns, ROI, and identifies "
                "optimization opportunities. Supports multi-platform analysis."
            ),
            category=ToolCategory.AGENT_CUSTOM,
            parameters=[
                ToolParameter(
                    name="data",
                    type="object",
                    description="Performance data including metrics, campaigns, time periods",
                    required=True,
                ),
                ToolParameter(
                    name="focus_areas",
                    type="array",
                    description="Specific areas to focus analysis on",
                    required=False,
                    default=["roi", "ctr", "conversion"],
                ),
            ],
            returns="object with insights, trends, and recommendations",
            credit_cost=3.0,
            tags=["performance", "analysis", "ai", "optimization"],
        )

        super().__init__(metadata)

        self.gemini_client = gemini_client or GeminiClient()

    async def execute(
        self,
        parameters: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute performance analysis.

        Args:
            parameters: Tool parameters
            context: Execution context

        Returns:
            Analysis insights and recommendations

        Raises:
            ToolExecutionError: If analysis fails
        """
        data = parameters.get("data", {})
        focus_areas = parameters.get("focus_areas", ["roi", "ctr", "conversion"])

        log = logger.bind(
            tool=self.name,
            focus_areas=focus_areas,
            data_keys=list(data.keys()),
        )
        log.info("analyze_performance_start")

        try:
            # Build analysis prompt
            prompt = self._build_analysis_prompt(data, focus_areas)

            # Analyze using Gemini
            messages = [{"role": "user", "content": prompt}]

            analysis_text = await self.gemini_client.chat_completion(
                messages=messages,
                temperature=0.3,
            )

            log.info("analyze_performance_complete")

            return {
                "success": True,
                "insights": analysis_text,
                "focus_areas": focus_areas,
                "message": "Performance analysis completed",
            }

        except GeminiError as e:
            log.error("gemini_error", error=str(e))
            raise ToolExecutionError(
                message=f"Performance analysis failed: {e.message}",
                tool_name=self.name,
                error_code=e.code,
            )

        except Exception as e:
            log.error("unexpected_error", error=str(e), exc_info=True)
            raise ToolExecutionError(
                message=f"Unexpected error: {str(e)}",
                tool_name=self.name,
            )

    def _build_analysis_prompt(
        self,
        data: dict[str, Any],
        focus_areas: list[str],
    ) -> str:
        """Build performance analysis prompt.

        Args:
            data: Performance data
            focus_areas: Areas to focus on

        Returns:
            Analysis prompt
        """
        # Format data for prompt
        data_summary = self._format_data_summary(data)

        prompt = f"""Analyze the following advertising performance data:

{data_summary}

Focus Areas: {', '.join(focus_areas)}

Provide a comprehensive analysis including:
1. Key Performance Trends: What patterns do you see?
2. Strengths: What's working well?
3. Weaknesses: What needs improvement?
4. Opportunities: Where can we optimize?
5. Actionable Recommendations: Specific steps to improve performance

Be specific and data-driven in your analysis."""

        return prompt

    def _format_data_summary(self, data: dict[str, Any]) -> str:
        """Format data for prompt.

        Args:
            data: Performance data

        Returns:
            Formatted data summary
        """
        lines = []

        # Format metrics
        if "metrics" in data:
            lines.append("Metrics:")
            for key, value in data["metrics"].items():
                lines.append(f"  - {key}: {value}")

        # Format campaigns
        if "campaigns" in data:
            lines.append("\nCampaigns:")
            for campaign in data["campaigns"][:5]:  # Limit to 5
                name = campaign.get("name", "Unknown")
                spend = campaign.get("spend", 0)
                roas = campaign.get("roas", 0)
                lines.append(f"  - {name}: Spend ${spend}, ROAS {roas}")

        # Format time period
        if "time_period" in data:
            period = data["time_period"]
            lines.append(f"\nTime Period: {period.get('start')} to {period.get('end')}")

        return "\n".join(lines)


class DetectAnomalyTool(AgentTool):
    """Tool for detecting performance anomalies using Gemini.

    This tool analyzes performance data to detect unusual patterns,
    sudden changes, or anomalies that require attention.
    """

    def __init__(self, gemini_client: GeminiClient | None = None):
        """Initialize the detect anomaly tool.

        Args:
            gemini_client: Gemini client for anomaly detection
        """
        metadata = ToolMetadata(
            name="detect_anomaly_tool",
            description=(
                "Detect performance anomalies and unusual patterns in advertising data. "
                "Identifies sudden changes, outliers, and potential issues that need attention."
            ),
            category=ToolCategory.AGENT_CUSTOM,
            parameters=[
                ToolParameter(
                    name="data",
                    type="object",
                    description="Performance data with time series metrics",
                    required=True,
                ),
                ToolParameter(
                    name="sensitivity",
                    type="string",
                    description="Anomaly detection sensitivity level",
                    required=False,
                    default="medium",
                    enum=["low", "medium", "high"],
                ),
            ],
            returns="list of detected anomalies with severity and recommendations",
            credit_cost=2.0,
            tags=["performance", "anomaly", "detection", "ai"],
        )

        super().__init__(metadata)

        self.gemini_client = gemini_client or GeminiClient()

    async def execute(
        self,
        parameters: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute anomaly detection.

        Args:
            parameters: Tool parameters
            context: Execution context

        Returns:
            List of detected anomalies

        Raises:
            ToolExecutionError: If detection fails
        """
        data = parameters.get("data", {})
        sensitivity = parameters.get("sensitivity", "medium")

        log = logger.bind(tool=self.name, sensitivity=sensitivity)
        log.info("detect_anomaly_start")

        try:
            # Build detection prompt
            prompt = self._build_detection_prompt(data, sensitivity)

            # Detect using Gemini
            messages = [{"role": "user", "content": prompt}]

            detection_text = await self.gemini_client.chat_completion(
                messages=messages,
                temperature=0.2,
            )

            log.info("detect_anomaly_complete")

            return {
                "success": True,
                "anomalies": detection_text,
                "sensitivity": sensitivity,
                "message": "Anomaly detection completed",
            }

        except GeminiError as e:
            log.error("gemini_error", error=str(e))
            raise ToolExecutionError(
                message=f"Anomaly detection failed: {e.message}",
                tool_name=self.name,
                error_code=e.code,
            )

        except Exception as e:
            log.error("unexpected_error", error=str(e), exc_info=True)
            raise ToolExecutionError(
                message=f"Unexpected error: {str(e)}",
                tool_name=self.name,
            )

    def _build_detection_prompt(
        self,
        data: dict[str, Any],
        sensitivity: str,
    ) -> str:
        """Build anomaly detection prompt.

        Args:
            data: Performance data
            sensitivity: Detection sensitivity

        Returns:
            Detection prompt
        """
        # Format time series data
        data_summary = self._format_time_series(data)

        sensitivity_desc = {
            "low": "only major anomalies (>50% change)",
            "medium": "significant anomalies (>25% change)",
            "high": "all notable anomalies (>10% change)",
        }

        prompt = f"""Analyze this advertising performance data for anomalies:

{data_summary}

Detection Sensitivity: {sensitivity} - detect {sensitivity_desc.get(sensitivity, 'anomalies')}

For each anomaly detected, provide:
1. Metric affected
2. Severity (low/medium/high)
3. Description of the anomaly
4. Possible causes
5. Recommended actions

Format as a structured list."""

        return prompt

    def _format_time_series(self, data: dict[str, Any]) -> str:
        """Format time series data for prompt.

        Args:
            data: Performance data

        Returns:
            Formatted time series
        """
        lines = []

        if "time_series" in data:
            lines.append("Time Series Data:")
            for point in data["time_series"][:10]:  # Limit to 10 points
                date = point.get("date", "Unknown")
                metrics = point.get("metrics", {})
                lines.append(f"  {date}: {metrics}")

        return "\n".join(lines)


class GenerateRecommendationsTool(AgentTool):
    """Tool for generating optimization recommendations using Gemini.

    This tool generates actionable recommendations for improving
    advertising performance based on analysis results.
    """

    def __init__(self, gemini_client: GeminiClient | None = None):
        """Initialize the generate recommendations tool.

        Args:
            gemini_client: Gemini client for recommendation generation
        """
        metadata = ToolMetadata(
            name="generate_recommendations_tool",
            description=(
                "Generate actionable optimization recommendations based on performance analysis. "
                "Provides specific, prioritized steps to improve advertising results."
            ),
            category=ToolCategory.AGENT_CUSTOM,
            parameters=[
                ToolParameter(
                    name="analysis",
                    type="object",
                    description="Performance analysis results",
                    required=True,
                ),
                ToolParameter(
                    name="goals",
                    type="array",
                    description="Optimization goals (e.g., increase ROAS, reduce CPA)",
                    required=False,
                    default=["increase_roas"],
                ),
                ToolParameter(
                    name="budget_constraints",
                    type="object",
                    description="Budget constraints and limits",
                    required=False,
                ),
            ],
            returns="list of prioritized recommendations with expected impact",
            credit_cost=2.0,
            tags=["performance", "recommendations", "optimization", "ai"],
        )

        super().__init__(metadata)

        self.gemini_client = gemini_client or GeminiClient()

    async def execute(
        self,
        parameters: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute recommendation generation.

        Args:
            parameters: Tool parameters
            context: Execution context

        Returns:
            List of prioritized recommendations

        Raises:
            ToolExecutionError: If generation fails
        """
        analysis = parameters.get("analysis", {})
        goals = parameters.get("goals", ["increase_roas"])
        budget_constraints = parameters.get("budget_constraints")

        log = logger.bind(tool=self.name, goals=goals)
        log.info("generate_recommendations_start")

        try:
            # Build recommendation prompt
            prompt = self._build_recommendation_prompt(analysis, goals, budget_constraints)

            # Generate using Gemini
            messages = [{"role": "user", "content": prompt}]

            recommendations_text = await self.gemini_client.chat_completion(
                messages=messages,
                temperature=0.4,
            )

            log.info("generate_recommendations_complete")

            return {
                "success": True,
                "recommendations": recommendations_text,
                "goals": goals,
                "message": "Recommendations generated successfully",
            }

        except GeminiError as e:
            log.error("gemini_error", error=str(e))
            raise ToolExecutionError(
                message=f"Recommendation generation failed: {e.message}",
                tool_name=self.name,
                error_code=e.code,
            )

        except Exception as e:
            log.error("unexpected_error", error=str(e), exc_info=True)
            raise ToolExecutionError(
                message=f"Unexpected error: {str(e)}",
                tool_name=self.name,
            )

    def _build_recommendation_prompt(
        self,
        analysis: dict[str, Any],
        goals: list[str],
        budget_constraints: dict[str, Any] | None,
    ) -> str:
        """Build recommendation generation prompt.

        Args:
            analysis: Performance analysis
            goals: Optimization goals
            budget_constraints: Budget constraints

        Returns:
            Recommendation prompt
        """
        # Format analysis summary
        analysis_summary = str(analysis)[:1000]  # Limit length

        # Format goals
        goals_text = ", ".join(goals)

        # Format budget constraints
        budget_text = ""
        if budget_constraints:
            budget_text = f"\nBudget Constraints: {budget_constraints}"

        prompt = f"""Based on this performance analysis:

{analysis_summary}

Optimization Goals: {goals_text}{budget_text}

Generate specific, actionable recommendations:

For each recommendation, provide:
1. Action: What to do
2. Priority: High/Medium/Low
3. Expected Impact: Quantify the expected improvement
4. Implementation: How to implement
5. Timeline: When to implement

Prioritize recommendations by expected ROI and ease of implementation."""

        return prompt


# Factory function to create all performance tools
def create_performance_tools(
    gemini_client: GeminiClient | None = None,
) -> list[AgentTool]:
    """Create all performance tools.

    Args:
        gemini_client: Gemini client instance

    Returns:
        List of performance tools
    """
    return [
        AnalyzePerformanceTool(gemini_client=gemini_client),
        DetectAnomalyTool(gemini_client=gemini_client),
        GenerateRecommendationsTool(gemini_client=gemini_client),
    ]
