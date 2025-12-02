"""LangGraph state machine builder.

This module builds and compiles the AI Orchestrator LangGraph,
connecting all nodes with appropriate routing logic.

Architecture: Planning + Multi-step Execution
- router: Intent recognition
- planner: Task decomposition and planning
- executor: Unified tool execution (loop)
- analyzer: Result analysis and decision making
- respond: Response generation
- persist: Conversation persistence

Requirements: Architecture v2.0
"""

import structlog
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.core.routing import (
    after_respond,
    route_after_analyzer,
    route_after_executor,
    route_after_planner,
    route_after_router_v2,
)
from app.core.state import AgentState
from app.nodes.analyzer import analyzer_node
from app.nodes.executor import executor_node
from app.nodes.persist import persist_conversation_node
from app.nodes.planner import planner_node
from app.nodes.respond import respond_node
from app.nodes.router import router_node

logger = structlog.get_logger(__name__)


def build_agent_graph() -> CompiledStateGraph:
    """Build and compile the AI Orchestrator state graph.

    Graph Structure:
    ```
    [START] → router → (route_after_router)
                              ↓
                 ┌────────────┴────────────┐
                 ↓                         ↓
              planner                   respond
                 ↓                         ↓
         (route_after_planner)          persist
                 ↓                         ↓
        ┌────────┴────────┐              [END]
        ↓                 ↓
     executor          __end__ (wait for confirmation)
        ↓
    (route_after_executor)
        ↓
     analyzer
        ↓
    (route_after_analyzer)
        ↓
    ┌───┴───┬───────┐
    ↓       ↓       ↓
 executor planner respond
    ```

    The executor-analyzer loop enables multi-step execution:
    1. Planner creates an execution plan with steps
    2. Executor runs one step at a time
    3. Analyzer decides: continue (more steps), respond (done), or replan

    Returns:
        Compiled LangGraph with MemorySaver checkpointer

    Requirements: Architecture v2.0
    """
    logger.info("build_agent_graph_start")

    # Create the state graph
    workflow = StateGraph(AgentState)

    # =========================================================================
    # Add Nodes
    # =========================================================================

    # Router node - intent recognition
    workflow.add_node("router", router_node)

    # Planner node - task decomposition
    workflow.add_node("planner", planner_node)

    # Executor node - tool execution
    workflow.add_node("executor", executor_node)

    # Analyzer node - result analysis and decision
    workflow.add_node("analyzer", analyzer_node)

    # Response generator
    workflow.add_node("respond", respond_node)

    # Conversation persistence
    workflow.add_node("persist", persist_conversation_node)

    # =========================================================================
    # Set Entry Point
    # =========================================================================

    workflow.set_entry_point("router")

    # =========================================================================
    # Add Edges - Router to Planner/Respond
    # =========================================================================

    workflow.add_conditional_edges(
        "router",
        route_after_router_v2,
        {
            "planner": "planner",
            "respond": "respond",
        },
    )

    # =========================================================================
    # Add Edges - Planner to Executor/Wait
    # =========================================================================

    workflow.add_conditional_edges(
        "planner",
        route_after_planner,
        {
            "executor": "executor",
            "respond": "respond",
            "__end__": END,  # Wait for plan confirmation
        },
    )

    # =========================================================================
    # Add Edges - Executor to Analyzer
    # =========================================================================

    workflow.add_conditional_edges(
        "executor",
        route_after_executor,
        {
            "analyzer": "analyzer",
            "respond": "respond",
        },
    )

    # =========================================================================
    # Add Edges - Analyzer Loop
    # =========================================================================

    workflow.add_conditional_edges(
        "analyzer",
        route_after_analyzer,
        {
            "executor": "executor",  # Continue execution
            "planner": "planner",    # Replan
            "respond": "respond",    # Done or error
        },
    )

    # =========================================================================
    # Add Edges - Response to Persistence
    # =========================================================================

    workflow.add_conditional_edges(
        "respond",
        after_respond,
        {
            "persist": "persist",
            "__end__": END,
        },
    )

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
    from app.tools.setup import register_all_tools

    # Ensure tools are registered
    register_all_tools()

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
    from app.tools.setup import register_all_tools

    # Ensure tools are registered
    register_all_tools()

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
