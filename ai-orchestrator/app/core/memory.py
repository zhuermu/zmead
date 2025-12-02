"""Memory component for ReAct Agent.

The Memory component is responsible for:
1. Storing conversation history in Redis
2. Managing execution state persistence
3. Retrieving relevant context for planning
4. Maintaining conversation continuity

It uses Redis for storage with TTL-based expiration.
"""

import json
from datetime import datetime
from typing import Any

import structlog

from app.core.redis_client import get_redis

logger = structlog.get_logger(__name__)


class ConversationMessage:
    """Represents a message in the conversation."""

    def __init__(
        self,
        role: str,
        content: str,
        timestamp: datetime | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        """Initialize conversation message.

        Args:
            role: Message role (user, assistant, system)
            content: Message content
            timestamp: Message timestamp
            metadata: Additional metadata
        """
        self.role = role
        self.content = content
        self.timestamp = timestamp or datetime.utcnow()
        self.metadata = metadata or {}

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ConversationMessage":
        """Create from dictionary."""
        return cls(
            role=data["role"],
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            metadata=data.get("metadata", {}),
        )


class AgentMemory:
    """Memory component for the ReAct Agent.

    Manages conversation history and execution state persistence
    using Redis as the storage backend.

    Example:
        memory = AgentMemory()

        # Save conversation message
        await memory.add_message(
            session_id="session123",
            role="user",
            content="Generate an ad image",
        )

        # Get conversation history
        history = await memory.get_conversation_history(
            session_id="session123",
            limit=10,
        )

        # Save execution state
        await memory.save_state(
            session_id="session123",
            state_data={"step": 1, "status": "thinking"},
        )
    """

    def __init__(
        self,
        conversation_ttl: int = 86400,  # 24 hours
        state_ttl: int = 3600,  # 1 hour
        max_history_length: int = 50,
    ):
        """Initialize the memory component.

        Args:
            conversation_ttl: Conversation history TTL in seconds
            state_ttl: Execution state TTL in seconds
            max_history_length: Maximum number of messages to keep
        """
        self.conversation_ttl = conversation_ttl
        self.state_ttl = state_ttl
        self.max_history_length = max_history_length

        logger.info(
            "memory_initialized",
            conversation_ttl=conversation_ttl,
            state_ttl=state_ttl,
            max_history_length=max_history_length,
        )

    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Add a message to conversation history.

        Args:
            session_id: Session ID
            role: Message role (user, assistant, system)
            content: Message content
            metadata: Additional metadata
        """
        log = logger.bind(session_id=session_id, role=role)
        log.debug("add_message")

        try:
            redis = await get_redis()
            key = f"conversation:history:{session_id}"

            # Create message
            message = ConversationMessage(
                role=role,
                content=content,
                metadata=metadata,
            )

            # Add to list
            message_json = json.dumps(message.to_dict(), ensure_ascii=False)
            await redis.rpush(key, message_json)

            # Trim to max length
            await redis.ltrim(key, -self.max_history_length, -1)

            # Set TTL
            await redis.expire(key, self.conversation_ttl)

            log.debug("message_added")

        except Exception as e:
            log.error("add_message_error", error=str(e))
            raise

    async def get_conversation_history(
        self,
        session_id: str,
        limit: int | None = None,
    ) -> list[ConversationMessage]:
        """Get conversation history for a session.

        Args:
            session_id: Session ID
            limit: Maximum number of messages to retrieve (most recent)

        Returns:
            List of conversation messages
        """
        log = logger.bind(session_id=session_id, limit=limit)
        log.debug("get_conversation_history")

        try:
            redis = await get_redis()
            key = f"conversation:history:{session_id}"

            # Get messages
            if limit:
                messages_json = await redis.lrange(key, -limit, -1)
            else:
                messages_json = await redis.lrange(key, 0, -1)

            # Parse messages
            messages = []
            for msg_json in messages_json:
                try:
                    msg_data = json.loads(msg_json)
                    messages.append(ConversationMessage.from_dict(msg_data))
                except (json.JSONDecodeError, KeyError) as e:
                    log.warning("invalid_message_format", error=str(e))
                    continue

            log.debug("conversation_history_retrieved", count=len(messages))

            return messages

        except Exception as e:
            log.error("get_conversation_history_error", error=str(e))
            return []

    async def get_conversation_context(
        self,
        session_id: str,
        max_messages: int = 10,
    ) -> list[dict[str, str]]:
        """Get conversation context formatted for LLM.

        Args:
            session_id: Session ID
            max_messages: Maximum number of messages to include

        Returns:
            List of message dicts with role and content
        """
        messages = await self.get_conversation_history(
            session_id=session_id,
            limit=max_messages,
        )

        return [{"role": msg.role, "content": msg.content} for msg in messages]

    async def clear_conversation(self, session_id: str) -> bool:
        """Clear conversation history for a session.

        Args:
            session_id: Session ID

        Returns:
            True if cleared successfully
        """
        log = logger.bind(session_id=session_id)
        log.info("clear_conversation")

        try:
            redis = await get_redis()
            key = f"conversation:history:{session_id}"
            await redis.delete(key)
            return True

        except Exception as e:
            log.error("clear_conversation_error", error=str(e))
            return False

    async def save_state(
        self,
        session_id: str,
        state_data: dict[str, Any],
        ttl: int | None = None,
    ) -> None:
        """Save execution state.

        Args:
            session_id: Session ID
            state_data: State data to save
            ttl: Optional TTL override
        """
        log = logger.bind(session_id=session_id)
        log.debug("save_state")

        try:
            redis = await get_redis()
            key = f"agent:state:{session_id}"

            # Add timestamp
            state_data["updated_at"] = datetime.utcnow().isoformat()

            # Save state
            state_json = json.dumps(state_data, ensure_ascii=False)
            await redis.set(key, state_json, ex=ttl or self.state_ttl)

            log.debug("state_saved")

        except Exception as e:
            log.error("save_state_error", error=str(e))
            raise

    async def load_state(
        self,
        session_id: str,
    ) -> dict[str, Any] | None:
        """Load execution state.

        Args:
            session_id: Session ID

        Returns:
            State data or None if not found
        """
        log = logger.bind(session_id=session_id)
        log.debug("load_state")

        try:
            redis = await get_redis()
            key = f"agent:state:{session_id}"

            state_json = await redis.get(key)
            if not state_json:
                return None

            state_data = json.loads(state_json)
            log.debug("state_loaded")

            return state_data

        except Exception as e:
            log.error("load_state_error", error=str(e))
            return None

    async def clear_state(self, session_id: str) -> bool:
        """Clear execution state.

        Args:
            session_id: Session ID

        Returns:
            True if cleared successfully
        """
        log = logger.bind(session_id=session_id)
        log.info("clear_state")

        try:
            redis = await get_redis()
            key = f"agent:state:{session_id}"
            await redis.delete(key)
            return True

        except Exception as e:
            log.error("clear_state_error", error=str(e))
            return False

    async def save_tool_result(
        self,
        session_id: str,
        tool_name: str,
        parameters: dict[str, Any],
        result: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        """Save tool execution result.

        Args:
            session_id: Session ID
            tool_name: Tool name
            parameters: Tool parameters
            result: Tool result
            error: Error message if failed
        """
        log = logger.bind(session_id=session_id, tool_name=tool_name)
        log.debug("save_tool_result")

        try:
            redis = await get_redis()
            key = f"agent:tools:{session_id}"

            # Create tool result entry
            tool_result = {
                "tool_name": tool_name,
                "parameters": parameters,
                "result": result,
                "error": error,
                "timestamp": datetime.utcnow().isoformat(),
            }

            # Add to list
            result_json = json.dumps(tool_result, ensure_ascii=False)
            await redis.rpush(key, result_json)

            # Trim to reasonable size
            await redis.ltrim(key, -100, -1)

            # Set TTL
            await redis.expire(key, self.state_ttl)

            log.debug("tool_result_saved")

        except Exception as e:
            log.error("save_tool_result_error", error=str(e))

    async def get_tool_results(
        self,
        session_id: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Get tool execution results.

        Args:
            session_id: Session ID
            limit: Maximum number of results to retrieve

        Returns:
            List of tool results
        """
        log = logger.bind(session_id=session_id, limit=limit)
        log.debug("get_tool_results")

        try:
            redis = await get_redis()
            key = f"agent:tools:{session_id}"

            # Get results
            results_json = await redis.lrange(key, -limit, -1)

            # Parse results
            results = []
            for result_json in results_json:
                try:
                    result_data = json.loads(result_json)
                    results.append(result_data)
                except json.JSONDecodeError as e:
                    log.warning("invalid_result_format", error=str(e))
                    continue

            log.debug("tool_results_retrieved", count=len(results))

            return results

        except Exception as e:
            log.error("get_tool_results_error", error=str(e))
            return []

    async def get_session_summary(
        self,
        session_id: str,
    ) -> dict[str, Any]:
        """Get summary of session data.

        Args:
            session_id: Session ID

        Returns:
            Summary dictionary
        """
        log = logger.bind(session_id=session_id)
        log.debug("get_session_summary")

        try:
            # Get conversation history
            messages = await self.get_conversation_history(session_id)

            # Get state
            state = await self.load_state(session_id)

            # Get tool results
            tool_results = await self.get_tool_results(session_id)

            summary = {
                "session_id": session_id,
                "message_count": len(messages),
                "has_state": state is not None,
                "tool_execution_count": len(tool_results),
                "last_activity": (
                    messages[-1].timestamp.isoformat() if messages else None
                ),
            }

            log.debug("session_summary_generated")

            return summary

        except Exception as e:
            log.error("get_session_summary_error", error=str(e))
            return {"session_id": session_id, "error": str(e)}

    async def clear_session(self, session_id: str) -> bool:
        """Clear all data for a session.

        Args:
            session_id: Session ID

        Returns:
            True if cleared successfully
        """
        log = logger.bind(session_id=session_id)
        log.info("clear_session")

        try:
            # Clear conversation
            await self.clear_conversation(session_id)

            # Clear state
            await self.clear_state(session_id)

            # Clear tool results
            redis = await get_redis()
            await redis.delete(f"agent:tools:{session_id}")

            log.info("session_cleared")
            return True

        except Exception as e:
            log.error("clear_session_error", error=str(e))
            return False
