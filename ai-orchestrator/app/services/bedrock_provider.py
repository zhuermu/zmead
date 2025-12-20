"""AWS Bedrock Model Provider.

This module provides integration with AWS Bedrock for LLM inference,
supporting Claude models via Bedrock's serverless API.

Features:
- Claude Sonnet 4.5 support
- Streaming responses
- AWS credentials management
- Error handling and retries
"""

import json
from typing import Any, AsyncIterator

import boto3
import structlog
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import get_settings
from app.services.model_provider import ModelProvider, ModelProviderError

logger = structlog.get_logger(__name__)


class BedrockProvider(ModelProvider):
    """AWS Bedrock model provider for Claude models.

    Supports:
    - global.anthropic.claude-sonnet-4-5-20250929-v1:0 (Claude Sonnet 4.5)
    - anthropic.claude-3-5-sonnet-20241022-v2:0 (Claude 3.5 Sonnet)
    """

    def __init__(
        self,
        region: str | None = None,
        model_id: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ):
        """Initialize Bedrock provider.

        Args:
            region: AWS region (defaults to settings)
            model_id: Bedrock model ID (defaults to settings)
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate
        """
        settings = get_settings()
        self.region = region or settings.bedrock_region
        self.model_id = model_id or settings.bedrock_default_model
        self.temperature = temperature
        self.max_tokens = max_tokens

        # Initialize Bedrock client
        try:
            self._client = boto3.client(
                service_name="bedrock-runtime",
                region_name=self.region,
            )
            logger.info(
                "bedrock_client_initialized",
                region=self.region,
                model_id=self.model_id,
            )
        except Exception as e:
            logger.error("bedrock_client_init_failed", error=str(e))
            raise ModelProviderError(f"Failed to initialize Bedrock client: {e}")

    async def generate(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> str:
        """Generate a response using Bedrock.

        Args:
            messages: List of conversation messages
            temperature: Optional temperature override
            max_tokens: Optional max tokens override
            **kwargs: Additional generation parameters

        Returns:
            Generated text response

        Raises:
            ModelProviderError: If generation fails
        """
        temp = temperature if temperature is not None else self.temperature
        max_tok = max_tokens if max_tokens is not None else self.max_tokens

        try:
            # Convert messages to Claude format
            claude_messages = self._convert_messages(messages)

            # Prepare request body
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "messages": claude_messages,
                "temperature": temp,
                "max_tokens": max_tok,
            }

            # Invoke model
            response = self._client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(body),
            )

            # Parse response
            response_body = json.loads(response["body"].read())
            content = response_body.get("content", [])

            if not content:
                raise ModelProviderError("Empty response from Bedrock")

            # Extract text from first content block
            return content[0].get("text", "")

        except (BotoCoreError, ClientError) as e:
            logger.error("bedrock_generation_failed", error=str(e))
            raise ModelProviderError(f"Bedrock generation failed: {e}")
        except Exception as e:
            logger.error("bedrock_unexpected_error", error=str(e))
            raise ModelProviderError(f"Unexpected error: {e}")

    async def generate_stream(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """Generate a streaming response using Bedrock.

        Args:
            messages: List of conversation messages
            temperature: Optional temperature override
            max_tokens: Optional max tokens override
            **kwargs: Additional generation parameters

        Yields:
            Text chunks as they are generated

        Raises:
            ModelProviderError: If generation fails
        """
        temp = temperature if temperature is not None else self.temperature
        max_tok = max_tokens if max_tokens is not None else self.max_tokens

        try:
            # Convert messages to Claude format
            claude_messages = self._convert_messages(messages)

            # Prepare request body
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "messages": claude_messages,
                "temperature": temp,
                "max_tokens": max_tok,
            }

            # Invoke model with streaming
            response = self._client.invoke_model_with_response_stream(
                modelId=self.model_id,
                body=json.dumps(body),
            )

            # Stream events
            for event in response.get("body", []):
                chunk = json.loads(event["chunk"]["bytes"])

                # Extract delta text
                if chunk.get("type") == "content_block_delta":
                    delta = chunk.get("delta", {})
                    if delta.get("type") == "text_delta":
                        text = delta.get("text", "")
                        if text:
                            yield text

        except (BotoCoreError, ClientError) as e:
            logger.error("bedrock_stream_failed", error=str(e))
            raise ModelProviderError(f"Bedrock streaming failed: {e}")
        except Exception as e:
            logger.error("bedrock_stream_unexpected_error", error=str(e))
            raise ModelProviderError(f"Unexpected streaming error: {e}")

    def _convert_messages(self, messages: list[dict[str, str]]) -> list[dict[str, Any]]:
        """Convert generic messages to Claude format.

        Args:
            messages: List of messages with 'role' and 'content'

        Returns:
            List of Claude-formatted messages
        """
        claude_messages = []

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            # Claude uses 'user' and 'assistant' roles
            if role == "system":
                # System messages are prepended as user messages
                claude_messages.append({
                    "role": "user",
                    "content": f"[SYSTEM] {content}",
                })
            elif role in ("user", "assistant"):
                claude_messages.append({
                    "role": role,
                    "content": content,
                })

        return claude_messages


__all__ = ["BedrockProvider"]
