"""Landing Page specialized agent.

This module implements a specialized agent for landing page generation
and optimization using the "Agents as Tools" pattern.
"""

import structlog
from strands import Agent, tool
from typing import Any

from app.services.model_factory import ModelFactory

logger = structlog.get_logger(__name__)


SYSTEM_PROMPT = """You are a specialized Landing Page Assistant for the AAE platform.

Your expertise includes:
- Generating landing pages from product information
- Optimizing landing page content and design
- Setting up A/B tests for landing pages
- Tracking conversion metrics
- Providing landing page best practices

You have access to tools for:
- Landing page generation
- Content optimization
- A/B test setup
- Conversion tracking

Always focus on conversion optimization and user experience.
When generating landing pages, consider mobile responsiveness, load times, and clear CTAs."""


@tool
async def landing_page_agent(query: str, user_id: str, **kwargs) -> str:
    """Process landing page generation and optimization requests.

    This specialized agent handles all landing page-related queries including
    generation, optimization, and A/B testing.

    Args:
        query: The user's landing page-related query
        user_id: User ID for context
        **kwargs: Additional context from invocation_state

    Returns:
        Response from the landing page agent
    """
    log = logger.bind(user_id=user_id, agent="landing_page")
    log.info("landing_page_agent_invoked", query_length=len(query))

    try:
        # Get model factory
        model_factory = ModelFactory()

        # Create model
        model = model_factory.create_model()

        # Import tools specific to landing pages
        from app.tools.landing_page import (
            generate_landing_page_tool,
            optimize_landing_page_tool,
            setup_ab_test_tool,
        )

        # Create specialized agent with landing page tools
        agent = Agent(
            system_prompt=SYSTEM_PROMPT,
            tools=[
                generate_landing_page_tool,
                optimize_landing_page_tool,
                setup_ab_test_tool,
            ],
            model=model,
        )

        # Execute the agent
        response = agent(query, invocation_state=kwargs)

        log.info("landing_page_agent_completed")
        return response

    except Exception as e:
        log.error("landing_page_agent_error", error=str(e), exc_info=True)
        return f"Error processing landing page request: {str(e)}"
