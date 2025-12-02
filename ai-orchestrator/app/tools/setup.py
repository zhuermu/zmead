"""Tool registration and setup.

This module handles the registration of all available tools
into the global ToolRegistry at application startup.

Usage:
    from app.tools.setup import register_all_tools

    # In main.py or startup
    register_all_tools()
"""

import structlog

from app.tools.registry import get_tool_registry

logger = structlog.get_logger(__name__)


def register_all_tools() -> None:
    """Register all available tools to the global registry.

    Should be called once at application startup.
    """
    logger.info("tool_setup_start")

    registry = get_tool_registry()

    # === Reporting Tools ===
    from app.tools.reporting.get_ad_performance import GetAdPerformanceTool

    registry.register(GetAdPerformanceTool())

    # === Creative Tools ===
    from app.tools.creative.generate_creative import GenerateCreativeTool

    registry.register(GenerateCreativeTool())

    # === Web Scraping Tools ===
    from app.tools.web.web_scraper import WebScrapeTool

    registry.register(WebScrapeTool())

    # === Campaign Tools (TODO) ===
    # from app.tools.campaign.create_campaign import CreateCampaignTool
    # registry.register(CreateCampaignTool())

    # === Market Tools (TODO) ===
    # from app.tools.market.get_competitor_ads import GetCompetitorAdsTool
    # registry.register(GetCompetitorAdsTool())

    logger.info(
        "tool_setup_complete",
        total_tools=len(registry),
        tools=registry.list_names(),
    )


def get_available_tool_names() -> list[str]:
    """Get list of all registered tool names.

    Returns:
        List of tool names
    """
    registry = get_tool_registry()
    return registry.list_names()
