"""Ad Performance specialized agent.

This module implements a specialized agent for ad performance analysis
and insights using the "Agents as Tools" pattern.
"""

import structlog
from strands import Agent, tool
from typing import Any

from app.services.model_factory import ModelFactory

logger = structlog.get_logger(__name__)


SYSTEM_PROMPT = """You are a specialized Ad Performance Analyst for the AAE platform.

Your expertise includes:
- Analyzing campaign performance metrics
- Detecting anomalies and trends
- Providing optimization recommendations
- Comparing performance across campaigns and platforms
- Generating performance reports and insights

You have access to tools for:
- Fetching real-time performance data
- Analyzing metrics and trends
- Detecting performance anomalies
- Generating performance reports

Always provide data-driven insights with specific, actionable recommendations.
When analyzing performance, consider industry benchmarks, historical trends, and campaign goals."""


@tool
async def ad_performance_agent(query: str, user_id: str, **kwargs) -> str:
    """Process ad performance analysis and reporting requests.

    This specialized agent handles all performance-related queries including
    metrics analysis, anomaly detection, and optimization recommendations.

    Args:
        query: The user's performance-related query
        user_id: User ID for context
        **kwargs: Additional context from invocation_state

    Returns:
        Response from the ad performance agent
    """
    log = logger.bind(user_id=user_id, agent="ad_performance")
    log.info("ad_performance_agent_invoked", query_length=len(query))

    try:
        # Get model factory
        model_factory = ModelFactory()

        # Create model
        model = model_factory.create_model()

        # Import tools specific to ad performance
        from app.tools.ad_performance import (
            fetch_performance_metrics_tool,
            analyze_performance_tool,
            detect_anomalies_tool,
        )

        # Create specialized agent with performance tools
        agent = Agent(
            system_prompt=SYSTEM_PROMPT,
            tools=[
                fetch_performance_metrics_tool,
                analyze_performance_tool,
                detect_anomalies_tool,
            ],
            model=model,
        )

        # Execute the agent
        response = agent(query, invocation_state=kwargs)

        log.info("ad_performance_agent_completed")
        return response

    except Exception as e:
        log.error("ad_performance_agent_error", error=str(e), exc_info=True)
        return f"Error processing performance request: {str(e)}"
