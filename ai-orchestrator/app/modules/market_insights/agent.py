"""Market Insights specialized agent.

This module implements a specialized agent for market analysis
and competitive intelligence using the "Agents as Tools" pattern.
"""

import structlog
from strands import Agent, tool
from typing import Any

from app.services.model_factory import ModelFactory

logger = structlog.get_logger(__name__)


SYSTEM_PROMPT = """You are a specialized Market Insights Analyst for the AAE platform.

Your expertise includes:
- Analyzing market trends and opportunities
- Tracking competitor activities and strategies
- Identifying target audience insights
- Providing industry benchmarks and comparisons
- Forecasting market trends

You have access to tools for:
- Market trend analysis
- Competitor tracking
- Audience research
- Industry benchmarking

Always provide strategic, data-driven insights that help users make informed decisions.
When analyzing markets, consider multiple data sources and provide context for your findings."""


@tool
async def market_insights_agent(query: str, user_id: str, **kwargs) -> str:
    """Process market analysis and competitive intelligence requests.

    This specialized agent handles all market insights queries including
    trend analysis, competitor tracking, and audience research.

    Args:
        query: The user's market insights query
        user_id: User ID for context
        **kwargs: Additional context from invocation_state

    Returns:
        Response from the market insights agent
    """
    log = logger.bind(user_id=user_id, agent="market_insights")
    log.info("market_insights_agent_invoked", query_length=len(query))

    try:
        # Get model factory
        model_factory = ModelFactory()

        # Create model
        model = model_factory.create_model()

        # Import tools specific to market insights
        from app.tools.market_insights import (
            analyze_market_trends_tool,
            track_competitors_tool,
            research_audience_tool,
        )

        # Create specialized agent with market insights tools
        agent = Agent(
            system_prompt=SYSTEM_PROMPT,
            tools=[
                analyze_market_trends_tool,
                track_competitors_tool,
                research_audience_tool,
            ],
            model=model,
        )

        # Execute the agent
        response = agent(query, invocation_state=kwargs)

        log.info("market_insights_agent_completed")
        return response

    except Exception as e:
        log.error("market_insights_agent_error", error=str(e), exc_info=True)
        return f"Error processing market insights request: {str(e)}"
