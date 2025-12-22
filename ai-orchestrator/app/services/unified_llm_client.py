"""Unified LLM Client - Dynamic model selection based on user preferences.

This module provides a unified interface for LLM operations that can use
either Gemini or Bedrock models based on user preferences.
"""

import json
import boto3
from botocore.config import Config
import structlog
from typing import Any

from app.core.config import get_settings
from app.services.gemini_client import GeminiClient, GeminiError

logger = structlog.get_logger(__name__)


class UnifiedLLMClient:
    """Unified LLM client that supports both Bedrock and Gemini models.

    This client dynamically selects the appropriate LLM provider based on
    user preferences passed in the context. Defaults to Bedrock (AWS Claude).
    """

    def __init__(self):
        """Initialize both Bedrock and Gemini clients."""
        settings = get_settings()

        # Initialize Bedrock client with extended timeout for long-running operations
        # (e.g., HTML generation which can take 30-120 seconds)
        bedrock_config = Config(
            connect_timeout=60,  # Connection timeout in seconds
            read_timeout=180,    # Read timeout in seconds (3 minutes for HTML generation)
            retries={'max_attempts': 2, 'mode': 'standard'}  # Retry with backoff
        )

        self.bedrock_client = boto3.client(
            service_name="bedrock-runtime",
            region_name=settings.bedrock_region,
            config=bedrock_config,
        )
        self.bedrock_model_id = settings.bedrock_default_model
        self.bedrock_temperature = settings.bedrock_temperature
        self.bedrock_max_tokens = settings.bedrock_max_tokens

        # Initialize Gemini client
        self.gemini_client = GeminiClient()

        logger.info(
            "unified_llm_client_initialized",
            bedrock_model=self.bedrock_model_id,
            bedrock_region=settings.bedrock_region,
            read_timeout=180,
        )

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        model_preferences: dict[str, Any] | None = None,
    ) -> str:
        """Generate chat completion using the selected model.

        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Temperature for generation (0.0-1.0)
            model_preferences: User's model preferences with 'provider' and optional 'model_id'

        Returns:
            Generated text response

        Raises:
            Exception: If generation fails
        """
        # Determine which provider to use
        provider = self._get_provider(model_preferences)

        log = logger.bind(
            provider=provider,
            temperature=temperature,
            message_count=len(messages),
        )
        log.info("unified_llm_chat_start")

        try:
            if provider == "bedrock":
                # Use Bedrock Claude (default)
                response = await self._call_bedrock(messages, temperature)
                log.info("unified_llm_chat_success", provider="bedrock")
                return response
            else:
                # Use Gemini (alternative)
                response = await self.gemini_client.chat_completion(
                    messages=messages,
                    temperature=temperature,
                )
                log.info("unified_llm_chat_success", provider="gemini")
                return response

        except GeminiError as e:
            log.error("unified_llm_chat_failed", error=str(e), provider=provider)
            raise
        except Exception as e:
            log.error("unified_llm_chat_unexpected_error", error=str(e), provider=provider)
            raise

    async def generate_structured_output(
        self,
        messages: list[dict[str, str]],
        schema: type,
        temperature: float = 0.1,
        model_preferences: dict[str, Any] | None = None,
    ) -> Any:
        """Generate structured output conforming to a Pydantic schema.

        Args:
            messages: List of message dicts
            schema: Pydantic model class for output validation
            temperature: Temperature for generation
            model_preferences: User's model preferences

        Returns:
            Instance of the schema class with generated data
        """
        provider = self._get_provider(model_preferences)

        log = logger.bind(
            provider=provider,
            schema=schema.__name__ if hasattr(schema, '__name__') else str(schema),
        )
        log.info("unified_llm_structured_start")

        try:
            if provider == "bedrock":
                # Bedrock doesn't have native structured output, use JSON mode (default)
                # Add instruction to return JSON
                enhanced_messages = messages.copy()
                enhanced_messages[-1]["content"] += "\n\nRespond with valid JSON only, no explanations."

                response_text = await self._call_bedrock(enhanced_messages, temperature)

                # Parse JSON and validate with schema
                import re

                # Clean up JSON response
                response_text = re.sub(r'^```json?\s*\n?', '', response_text, flags=re.IGNORECASE)
                response_text = re.sub(r'\n?```\s*$', '', response_text)
                response_text = response_text.strip()

                data = json.loads(response_text)
                result = schema(**data) if hasattr(schema, '__init__') else data

                log.info("unified_llm_structured_success", provider="bedrock")
                return result
            else:
                # Use Gemini's native structured output (alternative)
                result = await self.gemini_client.generate_structured_output(
                    messages=messages,
                    schema=schema,
                    temperature=temperature,
                )
                log.info("unified_llm_structured_success", provider="gemini")
                return result

        except Exception as e:
            log.error("unified_llm_structured_failed", error=str(e), provider=provider)
            raise

    def _get_provider(self, model_preferences: dict[str, Any] | Any | None) -> str:
        """Determine which provider to use based on model preferences.

        Args:
            model_preferences: User's model preferences dict or Pydantic model

        Returns:
            Provider name: "gemini" or "bedrock"
        """
        if not model_preferences:
            return "bedrock"  # Default to Bedrock

        # Handle Pydantic BaseModel objects
        if hasattr(model_preferences, "model_dump"):
            # Pydantic v2
            prefs_dict = model_preferences.model_dump()
        elif hasattr(model_preferences, "dict"):
            # Pydantic v1
            prefs_dict = model_preferences.dict()
        elif isinstance(model_preferences, dict):
            prefs_dict = model_preferences
        else:
            # Fallback to default
            return "bedrock"

        # Check for conversational_provider (for landing pages, use conversational model)
        provider = prefs_dict.get("conversational_provider") or prefs_dict.get("provider", "bedrock")

        # Normalize provider names
        if provider.lower() in ["bedrock", "claude", "aws"]:
            return "bedrock"
        else:
            return "gemini"

    async def _call_bedrock(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
    ) -> str:
        """Call AWS Bedrock Claude model.

        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Temperature for generation

        Returns:
            Generated text response

        Raises:
            Exception: If Bedrock call fails
        """
        import asyncio

        temp = temperature if temperature is not None else self.bedrock_temperature

        # Convert messages to Claude format
        claude_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            # Map "user" and "assistant" roles
            if role == "user":
                claude_messages.append({"role": "user", "content": content})
            elif role == "assistant":
                claude_messages.append({"role": "assistant", "content": content})
            elif role == "system":
                # For system messages, prepend to first user message
                if claude_messages and claude_messages[0]["role"] == "user":
                    claude_messages[0]["content"] = f"{content}\n\n{claude_messages[0]['content']}"
                else:
                    claude_messages.insert(0, {"role": "user", "content": content})

        # Prepare request body for Claude on Bedrock
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "messages": claude_messages,
            "temperature": temp,
            "max_tokens": self.bedrock_max_tokens,
        }

        # Call Bedrock in sync context using run_in_executor
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self.bedrock_client.invoke_model(
                modelId=self.bedrock_model_id,
                body=json.dumps(body),
            ),
        )

        # Parse response
        response_body = json.loads(response["body"].read())
        content = response_body.get("content", [])

        if not content:
            raise Exception("Empty response from Bedrock")

        # Extract text from first content block
        return content[0].get("text", "")
