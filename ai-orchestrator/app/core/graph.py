"""LangGraph state machine builder.

This module builds and compiles the AI Orchestrator LangGraph,
connecting all nodes with appropriate routing logic.

Requirements: 需求 4 (Orchestrator)
"""

import structlog
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.core.config import get_settings
from app.core.routing import (
    after_respond,
    route_by_intent,
    should_confirm,
)
from app.core.state import AgentState
from app.nodes.ad_engine_stub import ad_engine_stub_node
from app.nodes.campaign_automation_node import campaign_automation_node
from app.nodes.confirmation import human_confirmation_node
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
from app.nodes.router import router_node

logger = structlog.get_logger(__name__)


def build_agent_graph() -> CompiledStateGraph:
    """Build and compile the AI Orchestrator state graph.

    Graph Structure:
    ```
    [START] → router → (route_by_intent) → [module_stub]
                                              ↓
                                         (should_confirm)
                                              ↓
                                    ┌─────────┴─────────┐
                                    ↓                   ↓
                              confirmation           respond
                                    ↓                   ↓
                                  [END]             persist
                                                       ↓
                                                     [END]
    ```

    Returns:
        Compiled LangGraph with MemorySaver checkpointer

    Requirements: 需求 4
    """
    logger.info("build_agent_graph_start")

    # Create the state graph
    workflow = StateGraph(AgentState)

    # =========================================================================
    # Add Nodes
    # =========================================================================

    # Router node - intent recognition
    workflow.add_node("router", router_node)

    # Functional modules
    # Use real creative_node in production, stub in development/testing
    settings = get_settings()
    if settings.is_production:
        workflow.add_node("creative", creative_node)
    else:
        # In development, use real implementation by default
        # Set USE_CREATIVE_STUB=true to use stub
        import os
        use_stub = os.environ.get("USE_CREATIVE_STUB", "false").lower() == "true"
        if use_stub:
            workflow.add_node("creative", creative_stub_node)
        else:
            workflow.add_node("creative", creative_node)

    # Reporting module - use real implementation by default
    import os
    use_reporting_stub = os.environ.get("USE_REPORTING_STUB", "false").lower() == "true"
    if use_reporting_stub:
        workflow.add_node("reporting", reporting_stub_node)
    else:
        workflow.add_node("reporting", reporting_node)

    # Campaign Automation module - use real implementation by default
    use_campaign_automation_stub = os.environ.get("USE_CAMPAIGN_AUTOMATION_STUB", "false").lower() == "true"
    if use_campaign_automation_stub:
        workflow.add_node("ad_engine", ad_engine_stub_node)
    else:
        workflow.add_node("ad_engine", campaign_automation_node)

    # Landing Page module - use real implementation by default
    use_landing_page_stub = os.environ.get("USE_LANDING_PAGE_STUB", "false").lower() == "true"
    if use_landing_page_stub:
        workflow.add_node("landing_page", landing_page_stub_node)
    else:
        workflow.add_node("landing_page", landing_page_node)

    # Market Insights module - use real implementation by default
    use_market_insights_stub = os.environ.get("USE_MARKET_INSIGHTS_STUB", "false").lower() == "true"
    if use_market_insights_stub:
        workflow.add_node("market_insights", market_intel_stub_node)
    else:
        workflow.add_node("market_insights", market_insights_node)

    # Confirmation node
    workflow.add_node("human_confirmation", human_confirmation_node)

    # Response generator
    workflow.add_node("respond", respond_node)

    # Conversation persistence
    workflow.add_node("persist", persist_conversation_node)

    # =========================================================================
    # Set Entry Point
    # =========================================================================

    workflow.set_entry_point("router")

    # =========================================================================
    # Add Edges - Router to Modules
    # =========================================================================

    # Router routes to appropriate module based on intent
    workflow.add_conditional_edges(
        "router",
        route_by_intent,
        {
            "creative": "creative",  # Real implementation
            "creative_stub": "creative",  # Alias for backward compatibility
            "reporting": "reporting",  # Real implementation
            "reporting_stub": "reporting",  # Alias for backward compatibility
            "ad_engine": "ad_engine",  # Real implementation
            "ad_engine_stub": "ad_engine",  # Alias for backward compatibility
            "landing_page": "landing_page",  # Real implementation
            "landing_page_stub": "landing_page",  # Alias for backward compatibility
            "market_insights": "market_insights",  # Real implementation
            "market_intel_stub": "market_insights",  # Alias for backward compatibility
            "respond": "respond",
            "error_handler": "respond",  # Errors go to respond
        },
    )

    # =========================================================================
    # Add Edges - Modules to Confirmation Check
    # =========================================================================

    # Each module checks if confirmation is needed
    for module_node in [
        "creative",  # Real creative implementation
        "reporting",  # Real reporting implementation
        "ad_engine",  # Real campaign automation implementation
        "landing_page",  # Real landing page implementation
        "market_insights",  # Real market insights implementation
    ]:
        workflow.add_conditional_edges(
            module_node,
            should_confirm,
            {
                "confirm": "human_confirmation",
                "respond": "respond",
            },
        )

    # =========================================================================
    # Add Edges - Confirmation Flow
    # =========================================================================

    # Confirmation node ends (waits for user input)
    # When user confirms/cancels, graph is resumed with updated state
    workflow.add_edge("human_confirmation", END)

    # =========================================================================
    # Add Edges - Response to Persistence
    # =========================================================================

    # After response, persist conversation
    workflow.add_conditional_edges(
        "respond",
        after_respond,
        {
            "persist": "persist",
            "__end__": END,
        },
    )

    # Persistence ends the graph
    workflow.add_edge("persist", END)

    # =========================================================================
    # Compile with Checkpointer
    # =========================================================================

    # Use MemorySaver for state persistence
    # In production, could switch to Redis checkpointer
    memory = MemorySaver()

    compiled = workflow.compile(checkpointer=memory)

    logger.info("build_agent_graph_complete")

    return compiled


# Global graph instance (lazy initialization)
_agent_graph: CompiledStateGraph | None = None


def get_agent_graph() -> CompiledStateGraph:
    """Get or create the agent graph instance.

    Uses lazy initialization to avoid building the graph
    until it's actually needed.

    Returns:
        Compiled agent graph
    """
    global _agent_graph

    if _agent_graph is None:
        _agent_graph = build_agent_graph()

    return _agent_graph


def reset_agent_graph() -> None:
    """Reset the global agent graph instance.

    Useful for testing or when configuration changes.
    """
    global _agent_graph
    _agent_graph = None
    logger.info("agent_graph_reset")


async def run_agent(
    user_id: str,
    session_id: str,
    messages: list,
    config: dict | None = None,
) -> dict:
    """Run the agent graph with given input.

    Convenience function for executing the agent.

    Args:
        user_id: User identifier
        session_id: Session identifier
        messages: Input messages
        config: Optional LangGraph config

    Returns:
        Final state after execution
    """
    from app.core.state import create_initial_state

    graph = get_agent_graph()

    # Create initial state
    initial_state = create_initial_state(
        user_id=user_id,
        session_id=session_id,
        messages=messages,
    )

    # Build config with thread_id for checkpointing
    run_config = {
        "configurable": {
            "thread_id": session_id,
        },
    }

    if config:
        run_config.update(config)

    # Execute graph
    result = await graph.ainvoke(initial_state, run_config)

    return result


async def stream_agent(
    user_id: str,
    session_id: str,
    messages: list,
    config: dict | None = None,
):
    """Stream agent execution events.

    Yields events as the graph executes, useful for
    streaming responses to the client.

    Args:
        user_id: User identifier
        session_id: Session identifier
        messages: Input messages
        config: Optional LangGraph config

    Yields:
        LangGraph events
    """
    from app.core.state import create_initial_state

    graph = get_agent_graph()

    # Create initial state
    initial_state = create_initial_state(
        user_id=user_id,
        session_id=session_id,
        messages=messages,
    )

    # Build config
    run_config = {
        "configurable": {
            "thread_id": session_id,
        },
    }

    if config:
        run_config.update(config)

    # Stream events
    async for event in graph.astream_events(initial_state, run_config, version="v2"):
        yield event
