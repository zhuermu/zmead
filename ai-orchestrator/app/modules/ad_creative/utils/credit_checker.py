"""
Credit balance checker and manager for Ad Creative module.

Implements credit checking, reservation, deduction, and refund operations
through MCP communication with Web Platform.

Requirements: 9.1, 9.2, 9.3, 9.4, 9.5
"""

import uuid
from typing import Any

import structlog

from app.services.mcp_client import (
    MCPClient,
    MCPError,
    InsufficientCreditsError,
)
from ..models import CreditCheckResult


logger = structlog.get_logger(__name__)


class CreditCheckerError(Exception):
    """Base exception for credit checker errors."""

    def __init__(
        self,
        message: str,
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}


class CreditDeductionError(CreditCheckerError):
    """Raised when credit deduction fails."""

    def __init__(self, message: str = "Credit deduction failed"):
        super().__init__(message, error_code="6012")


class CreditRefundError(CreditCheckerError):
    """Raised when credit refund fails."""

    def __init__(self, message: str = "Credit refund failed"):
        super().__init__(message, error_code="6013")


class CreditChecker:
    """Checks and manages credit balance for ad creative operations.

    Credit rates:
    - Image generation: 0.5 credits/image
    - Bulk generation (10+): 0.4 credits/image (20% discount)
    - Creative analysis: 0.2 credits
    - Competitor analysis: 1.0 credits

    Implements:
    - check_and_reserve(): Check balance and reserve credits before operation
    - deduct(): Deduct credits after successful operation
    - refund(): Refund credits after failed operation
    - calculate_cost(): Calculate cost with bulk discount support
    """

    CREDIT_RATES = {
        "image_generation": 0.5,
        "image_generation_bulk": 0.4,
        "creative_analysis": 0.2,
        "competitor_analysis": 1.0,
    }

    BULK_THRESHOLD = 10  # Minimum count for bulk discount

    # Map internal operation types to MCP operation types
    OPERATION_TYPE_MAP = {
        "image_generation": "image_generation",
        "creative_analysis": "image_generation",  # Uses same MCP type
        "competitor_analysis": "competitor_analysis",
    }

    def __init__(self, mcp_client: MCPClient | None = None):
        """Initialize credit checker.

        Args:
            mcp_client: MCP client for Web Platform communication.
                       If None, a new client will be created.
        """
        self._mcp_client = mcp_client
        self._owns_client = mcp_client is None

    async def _get_mcp_client(self) -> MCPClient:
        """Get or create MCP client."""
        if self._mcp_client is None:
            self._mcp_client = MCPClient()
        return self._mcp_client

    async def close(self) -> None:
        """Close MCP client if we own it."""
        if self._owns_client and self._mcp_client is not None:
            await self._mcp_client.close()
            self._mcp_client = None


    def calculate_cost(self, operation: str, count: int = 1) -> float:
        """Calculate credit cost for an operation.

        Applies bulk discount (20% off) for image generation with 10+ items.

        Args:
            operation: Operation type (image_generation, creative_analysis, etc.)
            count: Number of items

        Returns:
            Total credit cost

        Examples:
            >>> checker = CreditChecker()
            >>> checker.calculate_cost("image_generation", 3)
            1.5  # 3 * 0.5
            >>> checker.calculate_cost("image_generation", 10)
            4.0  # 10 * 0.4 (bulk discount)
            >>> checker.calculate_cost("competitor_analysis", 1)
            1.0
        """
        if operation == "image_generation" and count >= self.BULK_THRESHOLD:
            return count * self.CREDIT_RATES["image_generation_bulk"]
        return count * self.CREDIT_RATES.get(operation, 0)

    def _get_mcp_operation_type(self, operation: str) -> str:
        """Map internal operation type to MCP operation type."""
        return self.OPERATION_TYPE_MAP.get(operation, "image_generation")

    def _generate_operation_id(self) -> str:
        """Generate a unique operation ID for tracking."""
        return f"ad_creative_{uuid.uuid4().hex[:12]}"


    async def check_and_reserve(
        self,
        user_id: str,
        operation: str,
        count: int = 1,
    ) -> CreditCheckResult:
        """Check credit balance and verify sufficient credits for operation.

        This method checks if the user has enough credits for the requested
        operation. It does NOT actually reserve or deduct credits - that
        happens in the deduct() method after successful operation.

        Args:
            user_id: User ID
            operation: Operation type (image_generation, creative_analysis, etc.)
            count: Number of items

        Returns:
            CreditCheckResult with:
            - allowed: True if user has sufficient credits
            - required_credits: Credits needed for operation
            - available_credits: User's current balance
            - error_code: "6011" if insufficient credits
            - error_message: User-friendly error message

        Raises:
            CreditCheckerError: If MCP communication fails
        """
        required = self.calculate_cost(operation, count)
        mcp_operation_type = self._get_mcp_operation_type(operation)

        log = logger.bind(
            user_id=user_id,
            operation=operation,
            count=count,
            required_credits=required,
        )
        log.info("credit_check_start")

        try:
            mcp = await self._get_mcp_client()
            result = await mcp.check_credit(
                user_id=user_id,
                estimated_credits=required,
                operation_type=mcp_operation_type,
            )

            available = float(result.get("available", 0))
            sufficient = result.get("sufficient", False)

            log.info(
                "credit_check_complete",
                sufficient=sufficient,
                available=available,
            )

            if not sufficient:
                return CreditCheckResult(
                    allowed=False,
                    required_credits=required,
                    available_credits=available,
                    error_code="6011",
                    error_message="Credit 余额不足，请充值后继续使用",
                )

            return CreditCheckResult(
                allowed=True,
                required_credits=required,
                available_credits=available,
            )

        except InsufficientCreditsError as e:
            log.warning(
                "credit_insufficient",
                required=e.required,
                available=e.available,
            )
            return CreditCheckResult(
                allowed=False,
                required_credits=required,
                available_credits=float(e.available or 0),
                error_code="6011",
                error_message="Credit 余额不足，请充值后继续使用",
            )

        except MCPError as e:
            log.error("credit_check_failed", error=str(e), code=e.code)
            raise CreditCheckerError(
                message=f"Credit check failed: {e.message}",
                error_code=e.code,
                details=e.details,
            )


    async def deduct(
        self,
        user_id: str,
        operation_id: str | None = None,
        credits: float | None = None,
        operation: str = "image_generation",
        count: int = 1,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Deduct credits after successful operation.

        Should be called after the operation completes successfully.
        If the operation fails, call refund() instead.

        Args:
            user_id: User ID
            operation_id: Unique operation ID for tracking. If None, one is generated.
            credits: Amount to deduct. If None, calculated from operation and count.
            operation: Operation type (used if credits is None)
            count: Number of items (used if credits is None)
            details: Additional details to store with transaction

        Returns:
            Transaction details including:
            - transaction_id: Unique transaction ID
            - amount: Amount deducted
            - balance_after: Balance after deduction
            - operation_id: Operation ID for refund tracking

        Raises:
            InsufficientCreditsError: If user doesn't have enough credits
            CreditDeductionError: If deduction fails
        """
        if credits is None:
            credits = self.calculate_cost(operation, count)

        if operation_id is None:
            operation_id = self._generate_operation_id()

        mcp_operation_type = self._get_mcp_operation_type(operation)

        log = logger.bind(
            user_id=user_id,
            operation_id=operation_id,
            credits=credits,
            operation=operation,
        )
        log.info("credit_deduct_start")

        try:
            mcp = await self._get_mcp_client()
            result = await mcp.deduct_credit(
                user_id=user_id,
                credits=credits,
                operation_type=mcp_operation_type,
                operation_id=operation_id,
                details=details,
            )

            log.info(
                "credit_deduct_complete",
                transaction_id=result.get("transaction_id"),
                balance_after=result.get("balance_after"),
            )

            return {
                "transaction_id": result.get("transaction_id"),
                "amount": credits,
                "balance_after": float(result.get("balance_after", 0)),
                "operation_id": operation_id,
            }

        except InsufficientCreditsError:
            log.warning("credit_deduct_insufficient")
            raise

        except MCPError as e:
            log.error("credit_deduct_failed", error=str(e), code=e.code)
            raise CreditDeductionError(
                f"Credit deduction failed: {e.message}"
            )


    async def refund(
        self,
        user_id: str,
        operation_id: str,
        credits: float,
        reason: str | None = None,
        operation: str = "image_generation",
    ) -> dict[str, Any]:
        """Refund credits after failed operation.

        Should be called when an operation fails after credits were deducted.
        Uses the operation_id from the original deduction for tracking.

        Args:
            user_id: User ID
            operation_id: Original operation ID from deduct()
            credits: Amount to refund
            reason: Reason for the refund (e.g., "generation_failed")
            operation: Operation type for MCP

        Returns:
            Transaction details including:
            - transaction_id: Refund transaction ID
            - amount: Amount refunded
            - balance_after: Balance after refund

        Raises:
            CreditRefundError: If refund fails
        """
        mcp_operation_type = self._get_mcp_operation_type(operation)

        log = logger.bind(
            user_id=user_id,
            operation_id=operation_id,
            credits=credits,
            reason=reason,
        )
        log.info("credit_refund_start")

        try:
            mcp = await self._get_mcp_client()
            result = await mcp.refund_credit(
                user_id=user_id,
                credits=credits,
                operation_type=mcp_operation_type,
                operation_id=operation_id,
                reason=reason,
            )

            log.info(
                "credit_refund_complete",
                transaction_id=result.get("transaction_id"),
                balance_after=result.get("balance_after"),
            )

            return {
                "transaction_id": result.get("transaction_id"),
                "amount": credits,
                "balance_after": float(result.get("balance_after", 0)),
            }

        except MCPError as e:
            log.error("credit_refund_failed", error=str(e), code=e.code)
            raise CreditRefundError(
                f"Credit refund failed: {e.message}"
            )

    async def get_balance(self, user_id: str) -> dict[str, Any]:
        """Get user's current credit balance.

        Args:
            user_id: User ID

        Returns:
            Balance info with:
            - gifted_credits: Free credits
            - purchased_credits: Paid credits
            - total_credits: Total available

        Raises:
            CreditCheckerError: If balance check fails
        """
        log = logger.bind(user_id=user_id)
        log.info("credit_balance_start")

        try:
            mcp = await self._get_mcp_client()
            result = await mcp.get_credit_balance(user_id)

            log.info(
                "credit_balance_complete",
                total=result.get("total_credits"),
            )

            return {
                "gifted_credits": float(result.get("gifted_credits", 0)),
                "purchased_credits": float(result.get("purchased_credits", 0)),
                "total_credits": float(result.get("total_credits", 0)),
            }

        except MCPError as e:
            log.error("credit_balance_failed", error=str(e), code=e.code)
            raise CreditCheckerError(
                message=f"Failed to get credit balance: {e.message}",
                error_code=e.code,
                details=e.details,
            )
