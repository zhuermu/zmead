"""Ad Creative specialized agent.

This module implements a specialized agent for ad creative generation,
analysis, and management using the "Agents as Tools" pattern.
"""

import structlog
from strands import Agent, tool
from typing import Any

from app.services.model_factory import ModelFactory

logger = structlog.get_logger(__name__)


SYSTEM_PROMPT = """You are a specialized Ad Creative Assistant for the AAE platform.

Your expertise includes:
- Generating ad images and videos using AI models
- Creating compelling ad copy and headlines
- Analyzing competitor creatives
- Suggesting creative variations for A/B testing
- Providing creative best practices and recommendations

You have access to tools for:
- Image generation (Qwen-Image model on SageMaker)
- Video generation (Wan2.2 model on SageMaker)
- Competitor creative analysis
- Creative performance insights

Always provide creative, actionable suggestions that align with advertising best practices.
When generating creatives, consider the target audience, platform requirements, and campaign goals."""


@tool
async def ad_creative_agent(query: str, user_id: str, **kwargs) -> str:
    """Process ad creative generation and analysis requests.

    This specialized agent handles all ad creative-related queries including
    image generation, video generation, copy creation, and creative analysis.

    Args:
        query: The user's creative-related query
        user_id: User ID for context
        **kwargs: Additional context from invocation_state

    Returns:
        Response from the ad creative agent
    """
    log = logger.bind(user_id=user_id, agent="ad_creative")
    log.info("ad_creative_agent_invoked", query_length=len(query))

    try:
        # Get model factory
        model_factory = ModelFactory()

        # Create model (use default provider from config)
        model = model_factory.create_model()

        # Import tools specific to ad creative
        from app.tools.ad_creative import (
            generate_image_tool,
            generate_video_tool,
            analyze_competitor_creative_tool,
        )

        # Create specialized agent with creative tools
        agent = Agent(
            system_prompt=SYSTEM_PROMPT,
            tools=[
                generate_image_tool,
                generate_video_tool,
                analyze_competitor_creative_tool,
            ],
            model=model,
        )

        # Execute the agent
        response = agent(query, invocation_state=kwargs)

        log.info("ad_creative_agent_completed")
        return response

    except Exception as e:
        log.error("ad_creative_agent_error", error=str(e), exc_info=True)
        return f"Error processing creative request: {str(e)}"
