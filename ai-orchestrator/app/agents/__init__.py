"""Sub-agents exposed as tools for the main orchestrator.

This module implements the Agents-as-Tools pattern where each capability
module is exposed as a callable function to the main Gemini 3 agent.

Architecture:
    Main Orchestrator (Gemini 3 Pro)
        ├── creative_agent()      - Image/Video generation
        ├── performance_agent()   - Ad reports and analytics
        ├── market_agent()        - Market insights and competitor analysis
        ├── landing_page_agent()  - Landing page generation
        └── campaign_agent()      - Campaign automation

Requirements: Architecture v3.0
"""

from app.agents.creative import CreativeAgent, creative_agent_tool
from app.agents.performance import PerformanceAgent, performance_agent_tool
from app.agents.market import MarketAgent, market_agent_tool
from app.agents.landing_page import LandingPageAgent, landing_page_agent_tool
from app.agents.campaign import CampaignAgent, campaign_agent_tool
from app.agents.registry import AgentRegistry, get_agent_registry

__all__ = [
    # Agents
    "CreativeAgent",
    "PerformanceAgent",
    "MarketAgent",
    "LandingPageAgent",
    "CampaignAgent",
    # Tool declarations
    "creative_agent_tool",
    "performance_agent_tool",
    "market_agent_tool",
    "landing_page_agent_tool",
    "campaign_agent_tool",
    # Registry
    "AgentRegistry",
    "get_agent_registry",
]
