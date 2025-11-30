"""Credit API Client for system-level credit management.

This module provides direct HTTP API calls to the backend for credit operations.
Credit management is a SYSTEM-LEVEL concern, NOT an MCP tool.

Why direct API instead of MCP:
- MCP is for exposing backend capabilities as tools that AI agents can understand and invoke
- Credit check/deduct is NOT something the AI model needs to understand or decide to do
- Credit consumption happens automatically when LLM calls consume tokens
- This is transparent to the AI model - it's infrastructure, not a tool

Requirements: 需求 12 (Credit Management)
"""

import asyncio
import uuid
from typing import Any

import httpx
import structlog

from app.core.config import get_settings

logger = structlog.get_logger(__name__)


class CreditError(Exception):
    """Base exception for credit errors."""

    def __init__(
        self,
        message: str,
        code: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}


class InsufficientCreditsError(CreditError):
    """Raised when user has insufficient credits."""

    def __init__(
        self,
        message: str = "Insufficient credits",
        required: float | None = None,
        available: float | None = None,
    ):
        details = {}
        if required is not None:
            details["required"] = required
        if available is not None:
            details["available"] = available
        super().__init__(message, code="6011", details=details)
        self.required = required
        self.available = available


class CreditAPIError(CreditError):
    """Raised when credit API call fails."""

    def __init__(self, message: str, code: str = "6012"):
        super().__init__(message, code=code)


class CreditClient:
    """Client for system-level credit management via direct HTTP API.

    This client communicates directly with the backend's credit API endpoints,
    NOT via MCP. Credit operations are system-level infrastructure concerns.

    Features:
    - Direct HTTP API calls (not MCP)
    - Service token authentication
    - Exponential backoff retry for transient errors
    - Connection pooling

    Example:
        async with CreditClient() as client:
            await client.check_credit(user_id, estimated_credits=5.0)
            await client.deduct_credit(user_id, credits=5.0, operation_type="generate_creative")
    """

    def __init__(
        self,
        base_url: str | None = None,
        service_token: str | None = None,
        timeout: float = 30.0,
        max_retries: int = 3,
        backoff_base: float = 1.0,
        backoff_factor: float = 2.0,
    ):
        """Initialize Credit Client.

        Args:
            base_url: Backend API URL. Defaults to settings.web_platform_url
            service_token: Service token for auth. Defaults to settings value
            timeout: Request timeout in seconds (default 30s)
            max_retries: Maximum retry attempts (default 3)
            backoff_base: Base wait time for retries in seconds (default 1s)
            backoff_factor: Multiplier for exponential backoff (default 2.0)
        """
        settings = get_settings()

        self.base_url = base_url or settings.web_platform_url
        self.service_token = service_token or settings.web_platform_service_token
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self.backoff_factor = backoff_factor

        # Credit API endpoints (direct HTTP, not MCP)
        self.check_credit_url = f"{self.base_url}/api/v1/credits/check"
        self.deduct_credit_url = f"{self.base_url}/api/v1/credits/deduct"
        self.refund_credit_url = f"{self.base_url}/api/v1/credits/refund"
        self.balance_url = f"{self.base_url}/api/v1/credits/balance"

        # HTTP client
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client with connection pooling."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                limits=httpx.Limits(
                    max_keepalive_connections=20,
                    max_connections=100,
                ),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.service_token}",
                    "User-Agent": "AI-Orchestrator/1.0",
                },
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> "CreditClient":
        """Async context manager entry."""
        await self._get_client()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()

    async def _make_request(
        self,
        method: str,
        url: str,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make HTTP request with retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            params: Query parameters
            json_data: JSON body data

        Returns:
            Response data

        Raises:
            CreditAPIError: If request fails after retries
            InsufficientCreditsError: If insufficient credits
        """
        request_id = str(uuid.uuid4())[:8]
        log = logger.bind(
            url=url,
            method=method,
            request_id=request_id,
        )

        last_error: Exception | None = None

        for attempt in range(self.max_retries):
            try:
                client = await self._get_client()

                if method.upper() == "GET":
                    response = await client.get(url, params=params)
                else:
                    response = await client.post(url, json=json_data)

                log.debug(
                    "credit_api_response",
                    status_code=response.status_code,
                    attempt=attempt + 1,
                )

                # Handle HTTP errors
                if response.status_code >= 500:
                    raise CreditAPIError(f"Server error: HTTP {response.status_code}")

                if response.status_code == 401:
                    raise CreditAPIError("Authentication failed", code="UNAUTHORIZED")

                if response.status_code == 403:
                    raise CreditAPIError("Permission denied", code="PERMISSION_DENIED")

                # Parse response
                try:
                    data = response.json()
                except Exception as e:
                    raise CreditAPIError(f"Invalid response format: {e}")

                # Check for insufficient credits error
                if response.status_code == 400:
                    error = data.get("error", {})
                    error_code = error.get("code", "")
                    if error_code == "INSUFFICIENT_CREDITS" or "insufficient" in error.get("message", "").lower():
                        raise InsufficientCreditsError(
                            message=error.get("message", "Credit 余额不足"),
                            required=error.get("details", {}).get("required"),
                            available=error.get("details", {}).get("available"),
                        )
                    raise CreditAPIError(error.get("message", "Credit API error"), code=error_code)

                # Success response
                if response.status_code in (200, 201):
                    return data.get("data", data)

                raise CreditAPIError(f"Unexpected status: {response.status_code}")

            except InsufficientCreditsError:
                # Don't retry insufficient credits
                raise

            except CreditAPIError as e:
                if "500" in str(e) or "Server error" in str(e):
                    # Retry server errors
                    last_error = e
                    if attempt < self.max_retries - 1:
                        wait_time = self.backoff_base * (self.backoff_factor ** attempt)
                        log.warning(
                            "credit_api_retry",
                            attempt=attempt + 1,
                            wait_seconds=wait_time,
                            error=str(e),
                        )
                        await asyncio.sleep(wait_time)
                        continue
                raise

            except httpx.TimeoutException:
                last_error = CreditAPIError("Request timed out")
                if attempt < self.max_retries - 1:
                    wait_time = self.backoff_base * (self.backoff_factor ** attempt)
                    log.warning(
                        "credit_api_timeout_retry",
                        attempt=attempt + 1,
                        wait_seconds=wait_time,
                    )
                    await asyncio.sleep(wait_time)
                    continue

            except httpx.HTTPError as e:
                last_error = CreditAPIError(f"HTTP error: {e}")
                if attempt < self.max_retries - 1:
                    wait_time = self.backoff_base * (self.backoff_factor ** attempt)
                    log.warning(
                        "credit_api_http_retry",
                        attempt=attempt + 1,
                        wait_seconds=wait_time,
                        error=str(e),
                    )
                    await asyncio.sleep(wait_time)
                    continue

        # All retries exhausted
        log.error("credit_api_failed", error=str(last_error))
        if last_error:
            raise last_error
        raise CreditAPIError("Unknown error during credit API call")

    async def check_credit(
        self,
        user_id: str,
        estimated_credits: float,
        operation_type: str | None = None,
    ) -> dict[str, Any]:
        """Check if user has sufficient credits for an operation.

        This is a SYSTEM-LEVEL operation, not an MCP tool call.

        Args:
            user_id: User ID
            estimated_credits: Estimated credits required
            operation_type: Type of operation (optional, for logging)

        Returns:
            Dict with 'sufficient', 'required', 'available' keys

        Raises:
            InsufficientCreditsError: If user doesn't have enough credits
            CreditAPIError: If check fails
        """
        log = logger.bind(
            user_id=user_id,
            operation_type=operation_type,
            estimated_credits=estimated_credits,
        )
        log.info("credit_check_start")

        result = await self._make_request(
            "POST",
            self.check_credit_url,
            json_data={
                "user_id": user_id,
                "amount": estimated_credits,
                "operation_type": operation_type,
            },
        )

        sufficient = result.get("sufficient", False)
        available = result.get("available", 0)

        log.info(
            "credit_check_complete",
            sufficient=sufficient,
            available=available,
        )

        if not sufficient:
            raise InsufficientCreditsError(
                message="Credit 余额不足，请充值后继续使用",
                required=estimated_credits,
                available=available,
            )

        return result

    async def deduct_credit(
        self,
        user_id: str,
        credits: float,
        operation_type: str,
        operation_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Deduct credits from user's balance.

        This is a SYSTEM-LEVEL operation, not an MCP tool call.

        Args:
            user_id: User ID
            credits: Amount of credits to deduct
            operation_type: Type of operation
            operation_id: Unique operation ID for tracking/refunds
            details: Additional details (model, tokens, etc.)

        Returns:
            Transaction details including transaction_id, balance_after

        Raises:
            InsufficientCreditsError: If user doesn't have enough credits
            CreditAPIError: If deduction fails
        """
        log = logger.bind(
            user_id=user_id,
            operation_type=operation_type,
            credits=credits,
            operation_id=operation_id,
        )
        log.info("credit_deduct_start")

        payload: dict[str, Any] = {
            "user_id": user_id,
            "amount": credits,
            "operation_type": operation_type,
        }

        if operation_id:
            payload["operation_id"] = operation_id
        if details:
            payload["details"] = details

        result = await self._make_request(
            "POST",
            self.deduct_credit_url,
            json_data=payload,
        )

        log.info(
            "credit_deduct_complete",
            transaction_id=result.get("transaction_id"),
            balance_after=result.get("balance_after"),
        )

        return result

    async def refund_credit(
        self,
        user_id: str,
        credits: float,
        operation_type: str,
        operation_id: str | None = None,
        reason: str | None = None,
    ) -> dict[str, Any]:
        """Refund credits to user's balance.

        This is a SYSTEM-LEVEL operation, not an MCP tool call.

        Args:
            user_id: User ID
            credits: Amount of credits to refund
            operation_type: Type of operation being refunded
            operation_id: Original operation ID
            reason: Reason for the refund

        Returns:
            Transaction details including transaction_id, balance_after

        Raises:
            CreditAPIError: If refund fails
        """
        log = logger.bind(
            user_id=user_id,
            operation_type=operation_type,
            credits=credits,
            operation_id=operation_id,
            reason=reason,
        )
        log.info("credit_refund_start")

        payload: dict[str, Any] = {
            "user_id": user_id,
            "amount": credits,
            "operation_type": operation_type,
        }

        if operation_id:
            payload["operation_id"] = operation_id
        if reason:
            payload["reason"] = reason

        result = await self._make_request(
            "POST",
            self.refund_credit_url,
            json_data=payload,
        )

        log.info(
            "credit_refund_complete",
            transaction_id=result.get("transaction_id"),
            balance_after=result.get("balance_after"),
        )

        return result

    async def get_balance(self, user_id: str) -> dict[str, Any]:
        """Get user's current credit balance.

        Args:
            user_id: User ID

        Returns:
            Balance info with gifted_credits, purchased_credits, total_credits
        """
        return await self._make_request(
            "GET",
            self.balance_url,
            params={"user_id": user_id},
        )


# Singleton instance for convenience
_credit_client: CreditClient | None = None


def get_credit_client() -> CreditClient:
    """Get or create the global credit client instance."""
    global _credit_client
    if _credit_client is None:
        _credit_client = CreditClient()
    return _credit_client


async def reset_credit_client() -> None:
    """Reset the global credit client (for testing)."""
    global _credit_client
    if _credit_client:
        await _credit_client.close()
        _credit_client = None
