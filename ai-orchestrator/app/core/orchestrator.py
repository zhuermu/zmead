"""Main Orchestrator using Gemini 3 with function calling.

This is the core orchestration layer that:
- Receives user messages
- Uses Gemini 3 Pro for understanding and reasoning
- Calls sub-agents via function calling
- Generates responses with native image generation

Architecture:
    User Message
         │
         ▼
    Gemini 3 Pro (Main Agent)
         │
         ├─► Native Image Generation (no tool needed)
         │
         └─► Function Calling (Sub-Agents)
                 ├── creative_agent
                 ├── performance_agent
                 ├── market_agent
                 ├── landing_page_agent
                 └── campaign_agent

Requirements: Architecture v3.0
"""

import asyncio
import json
from typing import Any, AsyncGenerator

import structlog
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from app.agents.registry import get_agent_registry
from app.agents.setup import register_all_agents
from app.core.state import AgentState
from app.services.gemini3_client import (
    GenerationConfig,
    Gemini3Client,
    Gemini3Error,
    get_gemini3_client,
)

logger = structlog.get_logger(__name__)

# System prompt for the main orchestrator
ORCHESTRATOR_SYSTEM_PROMPT = """你是 AAE（Automated Ad Engine）的 AI 助手，帮助用户管理广告投放。

## 你的能力

你可以直接生成图片（在回复中包含图片），也可以调用以下工具：

1. **creative_agent** - 生成广告素材
   - generate_image: 生成广告图片
   - generate_video: 生成广告视频
   - save_creative: 保存素材到素材库

2. **performance_agent** - 广告报表分析
   - get_report: 获取广告报表
   - analyze_performance: 分析广告表现
   - detect_anomalies: 检测异常
   - generate_recommendations: 生成优化建议

3. **market_agent** - 市场洞察
   - analyze_competitor: 竞品分析
   - get_trends: 市场趋势
   - generate_strategy: 生成策略

4. **landing_page_agent** - 落地页
   - create_landing_page: 创建落地页
   - translate_page: 翻译落地页

5. **campaign_agent** - 广告投放
   - create_campaign: 创建广告
   - update_budget: 调整预算
   - pause_campaign: 暂停广告
   - resume_campaign: 恢复广告

## 工作原则

1. **理解用户意图**：仔细理解用户想要什么，提取关键信息
2. **选择合适工具**：根据意图选择合适的 agent 和 action
3. **主动询问**：如果信息不足，主动询问用户
4. **清晰反馈**：操作完成后给出清晰的结果反馈
5. **安全确认**：高风险操作（暂停所有广告、大幅调整预算）前要确认

## 对话风格

- 专业但友好
- 简洁明了
- 使用中文回复
- 适当使用 emoji 增加亲和力
"""


class Orchestrator:
    """Main orchestrator using Gemini 3 with function calling.

    This class manages the conversation flow and coordinates sub-agents.

    Usage:
        orchestrator = Orchestrator()

        # Process a message
        response = await orchestrator.process_message(
            user_id="user123",
            session_id="session456",
            message="帮我生成 4 张广告图片",
        )

        # Stream response
        async for chunk in orchestrator.stream_message(...):
            print(chunk)
    """

    def __init__(self):
        self.gemini_client: Gemini3Client | None = None
        self._initialized = False

    def _ensure_initialized(self) -> None:
        """Ensure agents are registered and client is ready."""
        if not self._initialized:
            register_all_agents()
            self.gemini_client = get_gemini3_client()
            self._initialized = True

    async def process_message(
        self,
        user_id: str,
        session_id: str,
        message: str,
        conversation_history: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Process a user message and return response.

        Args:
            user_id: User identifier
            session_id: Session identifier
            message: User message text
            conversation_history: Optional conversation history

        Returns:
            Dict with response text, tool results, and metadata
        """
        self._ensure_initialized()

        log = logger.bind(user_id=user_id, session_id=session_id)
        log.info("orchestrator_process_message", message_preview=message[:100])

        # Build messages
        messages = self._build_messages(message, conversation_history)

        # Get agent registry
        registry = get_agent_registry()

        # Get tool declarations
        tools = registry.get_tool_declarations()

        # Get tool handlers with context
        handlers = registry.get_tool_handlers(user_id, session_id)

        try:
            # Use Gemini 3 with function calling
            result = await self.gemini_client.chat_with_tools(
                messages=messages,
                tools=tools,
                tool_handlers=handlers,
                config=GenerationConfig(
                    temperature=1.0,  # Gemini 3 recommends default
                    # Note: thinkingLevel is not supported in current Gemini API
                ),
                system_instruction=ORCHESTRATOR_SYSTEM_PROMPT,
            )

            log.info(
                "orchestrator_process_complete",
                iterations=result.get("iterations", 1),
            )

            return {
                "response": result.get("response", ""),
                "messages": result.get("messages", []),
                "success": True,
            }

        except Gemini3Error as e:
            log.error("orchestrator_gemini_error", error=str(e))
            return {
                "response": f"抱歉，处理请求时出错：{e}",
                "success": False,
                "error": str(e),
            }

    async def stream_message(
        self,
        user_id: str,
        session_id: str,
        message: str,
        conversation_history: list[dict[str, Any]] | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Stream response for a user message.

        Yields events as they occur:
        - {"type": "text", "content": "..."} - Text chunk
        - {"type": "tool_call", "tool": "...", "args": {...}} - Tool being called
        - {"type": "tool_result", "tool": "...", "result": {...}} - Tool result
        - {"type": "image", "data": "..."} - Generated image (base64)
        - {"type": "done"} - Stream complete

        Args:
            user_id: User identifier
            session_id: Session identifier
            message: User message text
            conversation_history: Optional conversation history

        Yields:
            Event dicts
        """
        self._ensure_initialized()

        log = logger.bind(user_id=user_id, session_id=session_id)
        log.info("orchestrator_stream_message", message_preview=message[:100])

        # Build messages
        messages = self._build_messages(message, conversation_history)

        # Get registry for tool calling
        registry = get_agent_registry()
        tools = registry.get_tool_declarations()
        handlers = registry.get_tool_handlers(user_id, session_id)

        try:
            # Yield thinking status
            yield {"type": "thinking", "message": "正在思考..."}

            # Use chat_with_tools which handles both text and tool calls
            result = await self.gemini_client.chat_with_tools(
                messages=messages,
                tools=tools,
                tool_handlers=handlers,
                config=GenerationConfig(temperature=1.0),
                system_instruction=ORCHESTRATOR_SYSTEM_PROMPT,
            )

            response_text = result.get("response", "")

            # Simulate streaming by splitting response into chunks
            if response_text:
                # Split into sentences or chunks for more natural streaming
                chunk_size = 20  # Characters per chunk
                for i in range(0, len(response_text), chunk_size):
                    chunk = response_text[i:i + chunk_size]
                    yield {"type": "text", "content": chunk}
                    # Small delay between chunks for natural streaming effect
                    import asyncio
                    await asyncio.sleep(0.01)

            yield {"type": "done"}

        except Gemini3Error as e:
            log.error("orchestrator_stream_error", error=str(e))
            yield {"type": "error", "error": str(e)}

    def _build_messages(
        self,
        current_message: str,
        history: list[dict[str, Any]] | None,
    ) -> list[dict[str, Any]]:
        """Build messages list for Gemini."""
        messages = []

        # Add history if provided
        if history:
            for msg in history:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                messages.append({"role": role, "content": content})

        # Add current message
        messages.append({"role": "user", "content": current_message})

        return messages


# Singleton instance
_orchestrator: Orchestrator | None = None


def get_orchestrator() -> Orchestrator:
    """Get or create Orchestrator singleton."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Orchestrator()
    return _orchestrator


async def process_user_message(
    user_id: str,
    session_id: str,
    message: str,
    history: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Convenience function to process a user message.

    Args:
        user_id: User ID
        session_id: Session ID
        message: User message
        history: Optional conversation history

    Returns:
        Response dict
    """
    orchestrator = get_orchestrator()
    return await orchestrator.process_message(user_id, session_id, message, history)


async def stream_user_message(
    user_id: str,
    session_id: str,
    message: str,
    history: list[dict[str, Any]] | None = None,
) -> AsyncGenerator[dict[str, Any], None]:
    """Convenience function to stream a user message response.

    Args:
        user_id: User ID
        session_id: Session ID
        message: User message
        history: Optional conversation history

    Yields:
        Event dicts
    """
    orchestrator = get_orchestrator()
    async for event in orchestrator.stream_message(user_id, session_id, message, history):
        yield event
