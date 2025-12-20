"""Campaign Automation specialized agent.

This module implements a specialized agent for campaign management
and automation using the "Agents as Tools" pattern.
"""

import structlog
from strands import Agent, tool
from typing import Any

from app.services.model_factory import ModelFactory

logger = structlog.get_logger(__name__)


SYSTEM_PROMPT = """You are a specialized Campaign Automation Assistant for the AAE platform.

Your expertise includes:
- Creating and managing ad campaigns
- Optimizing campaign budgets and bids
- Setting up automated rules and schedules
- Managing ad accounts and connections
- Pausing, resuming, and modifying campaigns

You have access to tools for:
- Campaign creation and management
- Budget optimization
- Automated rule setup
- Ad account management

Always confirm destructive actions (like deleting campaigns or changing budgets significantly).
When managing campaigns, consider platform-specific requirements and best practices."""


@tool
async def campaign_automation_agent(query: str, user_id: str, **kwargs) -> str:
    """Process campaign management and automation requests.

    This specialized agent handles all campaign-related queries including
    creation, optimization, and automated management.

    Args:
        query: The user's campaign-related query
        user_id: User ID for context
        **kwargs: Additional context from invocation_state

    Returns:
        Response from the campaign automation agent
    """
    log = logger.bind(user_id=user_id, agent="campaign_automation")
    log.info("campaign_automation_agent_invoked", query_length=len(query))

    try:
        # Get model factory
        model_factory = ModelFactory()

        # Create model
        model = model_factory.create_model()

        # Import tools specific to campaign automation
        from app.tools.campaign_automation import (
            create_campaign_tool,
            manage_campaign_tool,
            optimize_budget_tool,
        )

        # Create specialized agent with campaign tools
        agent = Agent(
            system_prompt=SYSTEM_PROMPT,
            tools=[
                create_campaign_tool,
                manage_campaign_tool,
                optimize_budget_tool,
            ],
            model=model,
        )

        # Execute the agent
        response = agent(query, invocation_state=kwargs)

        log.info("campaign_automation_agent_completed")
        return response

    except Exception as e:
        log.error("campaign_automation_agent_error", error=str(e), exc_info=True)
        return f"Error processing campaign request: {str(e)}"
