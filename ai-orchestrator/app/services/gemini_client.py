"""Gemini Client wrapper for AI model interactions.

This module provides the GeminiClient class for interacting with Google's
Gemini AI models via langchain-google-genai. It includes:
- Chat completion (Gemini 2.5 Pro)
- Structured output with Pydantic schemas
- Fast completion (Gemini 2.5 Flash)
- Error handling for API errors, rate limiting, quota exceeded
- Retry logic with exponential backoff
"""

import asyncio
from typing import Any, TypeVar

import structlog
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel

from app.core.config import get_settings

logger = structlog.get_logger(__name__)

# Type variable for structured output
T = TypeVar("T", bound=BaseModel)


class GeminiError(Exception):
    """Base exception for Gemini errors."""

    def __init__(
        self,
        message: str,
        code: str | None = None,
        retryable: bool = False,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.retryable = retryable


class GeminiRateLimitError(GeminiError):
    """Raised when rate limit is exceeded."""

    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(message, code="RATE_LIMIT", retryable=True)


class GeminiQuotaExceededError(GeminiError):
    """Raised when quota is exceeded."""

    def __init__(self, message: str = "Quota exceeded"):
        super().__init__(message, code="QUOTA_EXCEEDED", retryable=False)


class GeminiAPIError(GeminiError):
    """Raised for general API errors."""

    def __init__(self, message: str, retryable: bool = False):
        super().__init__(message, code="API_ERROR", retryable=retryable)


class GeminiTimeoutError(GeminiError):
    """Raised when request times out."""

    def __init__(self, message: str = "Request timed out"):
        super().__init__(message, code="TIMEOUT", retryable=True)


class GeminiClient:
    """Client for interacting with Google Gemini AI models.

    Uses langchain-google-genai for Gemini integration with:
    - Chat completion using Gemini 2.5 Pro
    - Structured output with Pydantic schemas
    - Fast completion using Gemini 2.5 Flash
    - Automatic retry with exponential backoff

    Example:
        client = GeminiClient()
        response = await client.chat_completion([
            {"role": "user", "content": "Hello!"}
        ])
    """

    def __init__(
        self,
        api_key: str | None = None,
        chat_model: str | None = None,
        fast_model: str | None = None,
        max_retries: int = 3,
        backoff_base: float = 1.0,
        backoff_factor: float = 2.0,
        timeout: float = 60.0,
    ):
        """Initialize Gemini Client.

        Args:
            api_key: Gemini API key. Defaults to settings value
            chat_model: Model for chat completion. Defaults to gemini-2.5-pro
            fast_model: Model for fast completion. Defaults to gemini-2.5-flash
            max_retries: Maximum retry attempts (default 3)
            backoff_base: Base wait time for retries in seconds (default 1s)
            backoff_factor: Multiplier for exponential backoff (default 2.0)
            timeout: Request timeout in seconds (default 60s)
        """
        settings = get_settings()

        self.api_key = api_key or settings.gemini_api_key
        self.chat_model_name = chat_model or settings.gemini_model_chat
        self.fast_model_name = fast_model or settings.gemini_model_fast
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self.backoff_factor = backoff_factor
        self.timeout = timeout

        # Initialize LLM instances
        self._chat_llm: ChatGoogleGenerativeAI | None = None
        self._fast_llm: ChatGoogleGenerativeAI | None = None

    def _get_chat_llm(self) -> ChatGoogleGenerativeAI:
        """Get or create chat LLM instance (Gemini 2.5 Pro)."""
        if self._chat_llm is None:
            self._chat_llm = ChatGoogleGenerativeAI(
                model=self.chat_model_name,
                google_api_key=self.api_key,
                temperature=0.1,
                max_retries=0,  # We handle retries ourselves
                timeout=self.timeout,
            )
        return self._chat_llm

    def _get_fast_llm(self) -> ChatGoogleGenerativeAI:
        """Get or create fast LLM instance (Gemini 2.5 Flash)."""
        if self._fast_llm is None:
            self._fast_llm = ChatGoogleGenerativeAI(
                model=self.fast_model_name,
                google_api_key=self.api_key,
                temperature=0.3,
                max_retries=0,  # We handle retries ourselves
                timeout=self.timeout,
            )
        return self._fast_llm

    def _convert_messages(
        self,
        messages: list[dict[str, str]],
    ) -> list[BaseMessage]:
        """Convert dict messages to LangChain message objects.

        Args:
            messages: List of message dicts with 'role' and 'content'

        Returns:
            List of LangChain BaseMessage objects
        """
        result: list[BaseMessage] = []

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "system":
                result.append(SystemMessage(content=content))
            elif role == "assistant":
                result.append(AIMessage(content=content))
            else:  # user or default
                result.append(HumanMessage(content=content))

        return result

    def _handle_error(self, error: Exception) -> GeminiError:
        """Convert exception to appropriate GeminiError.

        Args:
            error: Original exception

        Returns:
            Appropriate GeminiError subclass
        """
        error_str = str(error).lower()

        # Check for rate limiting
        if "rate" in error_str and "limit" in error_str:
            return GeminiRateLimitError(str(error))

        # Check for quota exceeded
        if "quota" in error_str or "exceeded" in error_str:
            return GeminiQuotaExceededError(str(error))

        # Check for timeout
        if "timeout" in error_str or "timed out" in error_str:
            return GeminiTimeoutError(str(error))

        # Check for retryable errors
        retryable = any(
            keyword in error_str for keyword in ["503", "500", "unavailable", "internal"]
        )

        return GeminiAPIError(str(error), retryable=retryable)

    async def _execute_with_retry(
        self,
        func,
        log: Any,
        operation: str,
    ) -> Any:
        """Execute function with retry logic.

        Args:
            func: Async function to execute
            log: Bound logger
            operation: Operation name for logging

        Returns:
            Function result

        Raises:
            GeminiError: If all retries fail
        """
        last_error: GeminiError | None = None

        for attempt in range(self.max_retries):
            try:
                return await func()

            except Exception as e:
                gemini_error = self._handle_error(e)
                last_error = gemini_error

                if not gemini_error.retryable:
                    log.error(
                        f"{operation}_failed",
                        error=str(e),
                        code=gemini_error.code,
                        retryable=False,
                    )
                    raise gemini_error

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
                        code=gemini_error.code,
                    )
                    raise gemini_error

        # Should not reach here
        if last_error:
            raise last_error
        raise GeminiAPIError("Unknown error")

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
    ) -> str:
        """Generate chat completion using Gemini 2.5 Pro.

        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Optional temperature override (0.0-1.0)

        Returns:
            Generated response text

        Raises:
            GeminiError: If generation fails
        """
        log = logger.bind(
            model=self.chat_model_name,
            message_count=len(messages),
        )
        log.info("chat_completion_start")

        llm = self._get_chat_llm()

        if temperature is not None:
            llm = llm.bind(temperature=temperature)

        langchain_messages = self._convert_messages(messages)

        async def _invoke():
            response = await llm.ainvoke(langchain_messages)
            return response.content

        result = await self._execute_with_retry(_invoke, log, "chat_completion")

        log.info(
            "chat_completion_complete",
            response_length=len(result) if result else 0,
        )

        return result

    async def structured_output(
        self,
        messages: list[dict[str, str]],
        schema: type[T],
        temperature: float | None = None,
    ) -> T:
        """Generate structured output using Gemini 2.5 Pro.

        Uses Pydantic schema for structured output parsing.

        Args:
            messages: List of message dicts with 'role' and 'content'
            schema: Pydantic model class for output structure
            temperature: Optional temperature override (0.0-1.0)

        Returns:
            Parsed Pydantic model instance

        Raises:
            GeminiError: If generation fails
        """
        log = logger.bind(
            model=self.chat_model_name,
            schema=schema.__name__,
            message_count=len(messages),
        )
        log.info("structured_output_start")

        llm = self._get_chat_llm()

        if temperature is not None:
            llm = llm.bind(temperature=temperature)

        # Use with_structured_output for reliable parsing
        structured_llm = llm.with_structured_output(schema)

        langchain_messages = self._convert_messages(messages)

        async def _invoke():
            return await structured_llm.ainvoke(langchain_messages)

        result = await self._execute_with_retry(_invoke, log, "structured_output")

        log.info("structured_output_complete")

        return result

    async def fast_completion(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
    ) -> str:
        """Generate fast completion using Gemini 2.5 Flash.

        Use this for quick responses where speed is more important
        than reasoning depth.

        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Optional temperature override (0.0-1.0)

        Returns:
            Generated response text

        Raises:
            GeminiError: If generation fails
        """
        log = logger.bind(
            model=self.fast_model_name,
            message_count=len(messages),
        )
        log.info("fast_completion_start")

        llm = self._get_fast_llm()

        if temperature is not None:
            llm = llm.bind(temperature=temperature)

        langchain_messages = self._convert_messages(messages)

        async def _invoke():
            response = await llm.ainvoke(langchain_messages)
            return response.content

        result = await self._execute_with_retry(_invoke, log, "fast_completion")

        log.info(
            "fast_completion_complete",
            response_length=len(result) if result else 0,
        )

        return result

    async def fast_structured_output(
        self,
        messages: list[dict[str, str]],
        schema: type[T],
        temperature: float | None = None,
    ) -> T:
        """Generate fast structured output using Gemini 2.5 Flash.

        Args:
            messages: List of message dicts with 'role' and 'content'
            schema: Pydantic model class for output structure
            temperature: Optional temperature override (0.0-1.0)

        Returns:
            Parsed Pydantic model instance

        Raises:
            GeminiError: If generation fails
        """
        log = logger.bind(
            model=self.fast_model_name,
            schema=schema.__name__,
            message_count=len(messages),
        )
        log.info("fast_structured_output_start")

        llm = self._get_fast_llm()

        if temperature is not None:
            llm = llm.bind(temperature=temperature)

        structured_llm = llm.with_structured_output(schema)

        langchain_messages = self._convert_messages(messages)

        async def _invoke():
            return await structured_llm.ainvoke(langchain_messages)

        result = await self._execute_with_retry(_invoke, log, "fast_structured_output")

        log.info("fast_structured_output_complete")

        return result
