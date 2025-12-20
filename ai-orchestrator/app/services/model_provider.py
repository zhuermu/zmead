"""Multi-provider AI model architecture.

This module provides an abstract base class for AI model providers and
concrete implementations for different providers (Gemini, AWS Bedrock, SageMaker).

The architecture supports:
- Unified interface for chat completion across providers
- Streaming responses
- Structured output with Pydantic schemas
- Provider-specific configuration
- Error handling and retry logic
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, TypeVar

import structlog
from pydantic import BaseModel

logger = structlog.get_logger(__name__)

# Type variable for structured output
T = TypeVar("T", bound=BaseModel)


class ModelProviderError(Exception):
    """Base exception for model provider errors."""

    def __init__(
        self,
        message: str,
        code: str | None = None,
        retryable: bool = False,
        provider: str | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.retryable = retryable
        self.provider = provider


class ModelProvider(ABC):
    """Abstract base class for AI model providers.

    All model providers must implement this interface to ensure
    consistent behavior across different AI services.

    Example:
        provider = GeminiProvider(api_key="...")
        response = await provider.chat_completion([
            {"role": "user", "content": "Hello!"}
        ])
    """

    def __init__(
        self,
        provider_name: str,
        max_retries: int = 3,
        backoff_base: float = 1.0,
        backoff_factor: float = 2.0,
        timeout: float = 60.0,
    ):
        """Initialize model provider.

        Args:
            provider_name: Name of the provider (e.g., "gemini", "bedrock")
            max_retries: Maximum retry attempts
            backoff_base: Base wait time for retries in seconds
            backoff_factor: Multiplier for exponential backoff
            timeout: Request timeout in seconds
        """
        self.provider_name = provider_name
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self.backoff_factor = backoff_factor
        self.timeout = timeout

        logger.info(
            "model_provider_initialized",
            provider=provider_name,
            max_retries=max_retries,
            timeout=timeout,
        )

    @abstractmethod
    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """Generate chat completion.

        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Optional temperature override (0.0-1.0)
            max_tokens: Optional maximum tokens to generate

        Returns:
            Generated response text

        Raises:
            ModelProviderError: If generation fails
        """
        pass

    @abstractmethod
    async def chat_completion_stream(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        """Generate streaming chat completion.

        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Optional temperature override (0.0-1.0)
            max_tokens: Optional maximum tokens to generate

        Yields:
            str: Text chunks as they are generated

        Raises:
            ModelProviderError: If generation fails
        """
        pass

    @abstractmethod
    async def structured_output(
        self,
        messages: list[dict[str, str]],
        schema: type[T],
        temperature: float | None = None,
    ) -> T:
        """Generate structured output using Pydantic schema.

        Args:
            messages: List of message dicts with 'role' and 'content'
            schema: Pydantic model class for output structure
            temperature: Optional temperature override (0.0-1.0)

        Returns:
            Parsed Pydantic model instance

        Raises:
            ModelProviderError: If generation fails
        """
        pass

    async def _execute_with_retry(
        self,
        func,
        operation: str,
    ) -> Any:
        """Execute function with retry logic.

        Args:
            func: Async function to execute
            operation: Operation name for logging

        Returns:
            Function result

        Raises:
            ModelProviderError: If all retries fail
        """
        log = logger.bind(provider=self.provider_name, operation=operation)
        last_error: ModelProviderError | None = None

        for attempt in range(self.max_retries):
            try:
                return await func()

            except ModelProviderError as e:
                last_error = e

                if not e.retryable:
                    log.error(
                        f"{operation}_failed",
                        error=str(e),
                        code=e.code,
                        retryable=False,
                    )
                    raise

                if attempt < self.max_retries - 1:
                    wait_time = self.backoff_base * (self.backoff_factor**attempt)
                    log.warning(
                        f"{operation}_retry",
                        attempt=attempt + 1,
                        max_retries=self.max_retries,
                        wait_seconds=wait_time,
                        error=str(e),
                    )
                    await asyncio.sleep(wait_time)
                else:
                    log.error(
                        f"{operation}_failed",
                        attempt=attempt + 1,
                        error=str(e),
                        code=e.code,
                    )
                    raise

            except Exception as e:
                # Convert unknown exceptions to ModelProviderError
                error = ModelProviderError(
                    message=str(e),
                    code="UNKNOWN_ERROR",
                    retryable=True,
                    provider=self.provider_name,
                )
                last_error = error

                if attempt < self.max_retries - 1:
                    wait_time = self.backoff_base * (self.backoff_factor**attempt)
                    log.warning(
                        f"{operation}_retry",
                        attempt=attempt + 1,
                        max_retries=self.max_retries,
                        wait_seconds=wait_time,
                        error=str(e),
                    )
                    await asyncio.sleep(wait_time)
                else:
                    log.error(
                        f"{operation}_failed",
                        attempt=attempt + 1,
                        error=str(e),
                    )
                    raise error

        # Should not reach here
        if last_error:
            raise last_error
        raise ModelProviderError(
            "Unknown error",
            code="UNKNOWN_ERROR",
            provider=self.provider_name,
        )

    def _handle_error(self, error: Exception) -> ModelProviderError:
        """Convert exception to ModelProviderError.

        Args:
            error: Original exception

        Returns:
            ModelProviderError with appropriate code and retryable flag
        """
        error_str = str(error).lower()

        # Check for rate limiting
        if "rate" in error_str and "limit" in error_str:
            return ModelProviderError(
                message=str(error),
                code="RATE_LIMIT",
                retryable=True,
                provider=self.provider_name,
            )

        # Check for quota exceeded
        if "quota" in error_str or "exceeded" in error_str:
            return ModelProviderError(
                message=str(error),
                code="QUOTA_EXCEEDED",
                retryable=False,
                provider=self.provider_name,
            )

        # Check for timeout
        if "timeout" in error_str or "timed out" in error_str:
            return ModelProviderError(
                message=str(error),
                code="TIMEOUT",
                retryable=True,
                provider=self.provider_name,
            )

        # Check for retryable errors
        retryable = any(
            keyword in error_str
            for keyword in ["503", "500", "unavailable", "internal"]
        )

        return ModelProviderError(
            message=str(error),
            code="API_ERROR",
            retryable=retryable,
            provider=self.provider_name,
        )
