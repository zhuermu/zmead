"""Simplified LangGraph state machine (Architecture v3.0).

This is a much simpler graph that leverages Gemini 3's native capabilities:
- Native image generation (no separate tool needed)
- Function calling for sub-agents
- Simplified flow: router → orchestrator → respond

The complexity is moved from graph routing to Gemini's function calling.

Architecture:
    [START] → orchestrator → persist → [END]

The orchestrator node handles:
1. Understanding user intent
2. Calling sub-agents via function calling
3. Generating response (including images)

Requirements: Architecture v3.0
"""

import structlog
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.core.state import AgentState
from app.agents.setup import register_all_agents

logger = structlog.get_logger(__name__)


async def orchestrator_node(state: AgentState) -> dict:
    """Main orchestrator node using Gemini 3 function calling.

    This single node handles:
    1. Understanding user message
    2. Calling appropriate sub-agents
    3. Generating final response

    Args:
        state: Current agent state

    Returns:
        State updates with response
    """
    from langchain_core.messages import AIMessage
    from app.core.orchestrator import get_orchestrator

    log = logger.bind(
        user_id=state.get("user_id"),
        session_id=state.get("session_id"),
    )
    log.info("orchestrator_node_start")

    # Get messages
    messages = state.get("messages", [])
    if not messages:
        return {
            "messages": [AIMessage(content="请问有什么可以帮您？")],
        }

    # Get last user message
    last_message = messages[-1]
    user_message = last_message.content if hasattr(last_message, "content") else str(last_message)

    # Build conversation history
    history = []
    for msg in messages[:-1]:
        role = "assistant" if msg.type == "ai" else "user"
        history.append({"role": role, "content": msg.content})

    # Process with orchestrator
    orchestrator = get_orchestrator()
    result = await orchestrator.process_message(
        user_id=state.get("user_id", ""),
        session_id=state.get("session_id", ""),
        message=user_message,
        conversation_history=history,
    )

    log.info(
        "orchestrator_node_complete",
        success=result.get("success"),
    )

    # Build response message
    response_text = result.get("response", "抱歉，处理请求时出错。")

    return {
        "messages": [AIMessage(content=response_text)],
        "completed_results": result.get("tool_results", []),
    }


async def persist_node(state: AgentState) -> dict:
    """Persist conversation to storage.

    Args:
        state: Current agent state

    Returns:
        Empty dict (no state changes)
    """
    log = logger.bind(
        user_id=state.get("user_id"),
        session_id=state.get("session_id"),
    )
    log.info("persist_node")

    # TODO: Persist to Redis/Database if needed
    # The LangGraph checkpointer handles basic state persistence

    return {}


def build_agent_graph_v3() -> CompiledStateGraph:
    """Build simplified agent graph (v3.0).

    Graph Structure:
        [START] → orchestrator → persist → [END]

    Returns:
        Compiled LangGraph with MemorySaver checkpointer
    """
    logger.info("build_agent_graph_v3_start")

    # Ensure agents are registered
    register_all_agents()

    # Create the state graph
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("orchestrator", orchestrator_node)
    workflow.add_node("persist", persist_node)

    # Set entry point
    workflow.set_entry_point("orchestrator")

    # Add edges
    workflow.add_edge("orchestrator", "persist")
    workflow.add_edge("persist", END)

    # Compile with checkpointer
    memory = MemorySaver()
    compiled = workflow.compile(checkpointer=memory)

    logger.info("build_agent_graph_v3_complete")

    return compiled


# Global graph instance
_agent_graph_v3: CompiledStateGraph | None = None


def get_agent_graph_v3() -> CompiledStateGraph:
    """Get or create the v3 agent graph instance."""
    global _agent_graph_v3

    if _agent_graph_v3 is None:
        _agent_graph_v3 = build_agent_graph_v3()

    return _agent_graph_v3


def reset_agent_graph_v3() -> None:
    """Reset the global agent graph instance."""
    global _agent_graph_v3
    _agent_graph_v3 = None
    logger.info("agent_graph_v3_reset")


async def run_agent_v3(
    user_id: str,
    session_id: str,
    messages: list,
    config: dict | None = None,
) -> dict:
    """Run the v3 agent graph.

    Args:
        user_id: User identifier
        session_id: Session identifier
        messages: Input messages
        config: Optional LangGraph config

    Returns:
        Final state after execution
    """
    from app.core.state import create_initial_state

    graph = get_agent_graph_v3()

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

    # Execute graph
    result = await graph.ainvoke(initial_state, run_config)

    return result


async def stream_agent_v3(
    user_id: str,
    session_id: str,
    messages: list,
    config: dict | None = None,
):
    """Stream v3 agent execution events.

    Args:
        user_id: User identifier
        session_id: Session identifier
        messages: Input messages
        config: Optional LangGraph config

    Yields:
        LangGraph events
    """
    from app.core.state import create_initial_state

    graph = get_agent_graph_v3()

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
