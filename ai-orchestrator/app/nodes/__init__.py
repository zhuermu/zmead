"""LangGraph nodes for AI Orchestrator.

This package contains all the nodes used in the AI Orchestrator
state machine, including:
- router: Intent recognition and routing
- creative_node: Ad Creative module (real implementation with Imagen 3)
- creative_stub: Ad Creative module (stub for testing)
- reporting_node: Ad Performance module (real implementation)
- reporting_stub: Ad Performance module (stub for testing)
- campaign_automation_node: Campaign Automation module (real implementation)
- ad_engine_stub: Campaign Automation module (stub for testing)
- market_insights_node: Market Insights module (real implementation)
- market_intel_stub: Market Insights module (stub for testing)
- landing_page_node: Landing Page module (real implementation)
- landing_page_stub: Landing Page module (stub for testing)
- respond: Response generation
- persist: Conversation persistence
- confirmation: Human confirmation for high-risk operations
"""

from app.nodes.ad_engine_stub import ad_engine_stub_node
from app.nodes.campaign_automation_node import campaign_automation_node
from app.nodes.confirmation import (
    check_confirmation_response,
    human_confirmation_node,
)
from app.nodes.creative_node import creative_node
from app.nodes.creative_stub import creative_stub_node
from app.nodes.landing_page_node import landing_page_node
from app.nodes.landing_page_stub import landing_page_stub_node
from app.nodes.market_insights_node import market_insights_node
from app.nodes.market_intel_stub import market_intel_stub_node
from app.nodes.persist import persist_conversation_node
from app.nodes.reporting_node import reporting_node
from app.nodes.reporting_stub import reporting_stub_node
from app.nodes.respond import respond_node
from app.nodes.router import IntentSchema, router_node

__all__ = [
    # Router
    "router_node",
    "IntentSchema",
    # Functional modules
    "creative_node",  # Real implementation with Imagen 3
    "creative_stub_node",  # Stub for testing
    "reporting_node",  # Real implementation
    "reporting_stub_node",  # Stub for testing
    "campaign_automation_node",  # Real implementation
    "ad_engine_stub_node",  # Stub for testing
    "market_insights_node",  # Real implementation
    "market_intel_stub_node",  # Stub for testing
    "landing_page_node",  # Real implementation
    "landing_page_stub_node",  # Stub for testing
    # Response and persistence
    "respond_node",
    "persist_conversation_node",
    # Confirmation
    "human_confirmation_node",
    "check_confirmation_response",
]
