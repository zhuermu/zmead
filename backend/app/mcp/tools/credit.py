"""MCP tools for credit management.

Implements tools for managing user credits:
- get_credit_balance: Get current credit balance
- check_credit: Check if user has sufficient credits
- deduct_credit: Deduct credits for an operation
- refund_credit: Refund credits for a failed operation
- get_credit_history: Get credit transaction history
- get_credit_config: Get current credit configuration
- estimate_credit: Estimate credit cost for an operation
"""

from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.mcp.registry import tool
from app.mcp.types import MCPToolParameter
from app.schemas.credit import OperationType
from app.services.credit import CreditService


@tool(
    name="get_credit_balance",
    description="Get the current credit balance for the user, including gifted and purchased credits.",
    parameters=[],
    category="credit",
)
async def get_credit_balance(
    user_id: int,
    db: AsyncSession,
) -> dict[str, Any]:
    """Get user's credit balance."""
    service = CreditService(db)
    balance = await service.get_balance(user_id)

    return {
        "gifted_credits": str(balance["gifted_credits"]),
        "purchased_credits": str(balance["purchased_credits"]),
        "total_credits": str(balance["total_credits"]),
    }


@tool(
    name="check_credit",
    description="Check if the user has sufficient credits for an operation. Returns true/false without deducting.",
    parameters=[
        MCPToolParameter(
            name="amount",
            type="number",
            description="Amount of credits required",
            required=True,
        ),
    ],
    category="credit",
)
async def check_credit(
    user_id: int,
    db: AsyncSession,
    amount: float,
) -> dict[str, Any]:
    """Check if user has sufficient credits."""
    service = CreditService(db)
    has_sufficient = await service.check_sufficient_credits(
        user_id,
        Decimal(str(amount)),
    )

    balance = await service.get_balance(user_id)

    return {
        "sufficient": has_sufficient,
        "required": str(amount),
        "available": str(balance["total_credits"]),
    }


@tool(
    name="deduct_credit",
    description="Deduct credits from user's balance for an operation. Deducts from gifted credits first, then purchased.",
    parameters=[
        MCPToolParameter(
            name="amount",
            type="number",
            description="Amount of credits to deduct",
            required=True,
        ),
        MCPToolParameter(
            name="operation_type",
            type="string",
            description="Type of operation consuming credits",
            required=True,
            enum=["chat", "image_generation", "video_generation", "landing_page", "competitor_analysis", "optimization_suggestion"],
        ),
        MCPToolParameter(
            name="operation_id",
            type="string",
            description="Unique ID for the operation (for tracking/refunds)",
            required=False,
        ),
        MCPToolParameter(
            name="details",
            type="object",
            description="Additional details (model, tokens, etc.)",
            required=False,
        ),
    ],
    category="credit",
)
async def deduct_credit(
    user_id: int,
    db: AsyncSession,
    amount: float,
    operation_type: str,
    operation_id: str | None = None,
    details: dict | None = None,
) -> dict[str, Any]:
    """Deduct credits from user's balance."""
    service = CreditService(db)

    # This will raise InsufficientCreditsError if not enough credits
    transaction = await service.deduct_credits(
        user_id=user_id,
        amount=Decimal(str(amount)),
        operation_type=OperationType(operation_type),
        operation_id=operation_id,
        details=details,
    )

    return {
        "transaction_id": transaction.id,
        "amount": str(transaction.amount),
        "from_gifted": str(transaction.from_gifted),
        "from_purchased": str(transaction.from_purchased),
        "balance_after": str(transaction.balance_after),
        "operation_type": transaction.operation_type,
        "operation_id": transaction.operation_id,
        "created_at": transaction.created_at.isoformat() if transaction.created_at else None,
    }


@tool(
    name="refund_credit",
    description="Refund credits to user's balance for a failed or cancelled operation.",
    parameters=[
        MCPToolParameter(
            name="amount",
            type="number",
            description="Amount of credits to refund",
            required=True,
        ),
        MCPToolParameter(
            name="operation_type",
            type="string",
            description="Type of operation being refunded",
            required=True,
            enum=["chat", "image_generation", "video_generation", "landing_page", "competitor_analysis", "optimization_suggestion"],
        ),
        MCPToolParameter(
            name="operation_id",
            type="string",
            description="Original operation ID",
            required=False,
        ),
        MCPToolParameter(
            name="reason",
            type="string",
            description="Reason for the refund",
            required=False,
        ),
    ],
    category="credit",
)
async def refund_credit(
    user_id: int,
    db: AsyncSession,
    amount: float,
    operation_type: str,
    operation_id: str | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    """Refund credits to user's balance."""
    service = CreditService(db)

    transaction = await service.refund_credits(
        user_id=user_id,
        amount=Decimal(str(amount)),
        operation_type=OperationType(operation_type),
        operation_id=operation_id,
        reason=reason,
    )

    return {
        "transaction_id": transaction.id,
        "amount": str(transaction.amount),
        "balance_after": str(transaction.balance_after),
        "operation_type": transaction.operation_type,
        "operation_id": transaction.operation_id,
        "created_at": transaction.created_at.isoformat() if transaction.created_at else None,
    }


@tool(
    name="get_credit_history",
    description="Get the user's credit transaction history with pagination.",
    parameters=[
        MCPToolParameter(
            name="page",
            type="integer",
            description="Page number (1-indexed)",
            required=False,
            default=1,
        ),
        MCPToolParameter(
            name="page_size",
            type="integer",
            description="Number of items per page (max 100)",
            required=False,
            default=20,
        ),
        MCPToolParameter(
            name="days",
            type="integer",
            description="Number of days to look back",
            required=False,
            default=30,
        ),
    ],
    category="credit",
)
async def get_credit_history(
    user_id: int,
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    days: int = 30,
) -> dict[str, Any]:
    """Get credit transaction history."""
    # Validate page_size
    page_size = min(page_size, 100)

    service = CreditService(db)
    result = await service.get_transaction_history(
        user_id=user_id,
        page=page,
        page_size=page_size,
        days=days,
    )

    # Convert to serializable format
    transactions = [
        {
            "id": t.id,
            "type": t.type,
            "amount": str(t.amount),
            "from_gifted": str(t.from_gifted),
            "from_purchased": str(t.from_purchased),
            "balance_after": str(t.balance_after),
            "operation_type": t.operation_type,
            "operation_id": t.operation_id,
            "details": t.details or {},
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
        for t in result["transactions"]
    ]

    return {
        "transactions": transactions,
        "total": result["total"],
        "page": result["page"],
        "page_size": result["page_size"],
        "has_more": result["has_more"],
    }


@tool(
    name="get_credit_config",
    description="Get the current credit configuration including rates for different operations.",
    parameters=[],
    category="credit",
)
async def get_credit_config(
    user_id: int,
    db: AsyncSession,
) -> dict[str, Any]:
    """Get credit configuration."""
    service = CreditService(db)
    config = await service.get_config_dict()

    return config


@tool(
    name="estimate_credit",
    description="Estimate the credit cost for an operation based on current configuration.",
    parameters=[
        MCPToolParameter(
            name="operation_type",
            type="string",
            description="Type of operation",
            required=True,
            enum=["chat", "image_generation", "video_generation", "landing_page", "competitor_analysis", "optimization_suggestion"],
        ),
        MCPToolParameter(
            name="model",
            type="string",
            description="AI model to use (for chat operations)",
            required=False,
            enum=["gemini_flash", "gemini_pro"],
        ),
        MCPToolParameter(
            name="input_tokens",
            type="integer",
            description="Estimated input tokens (for chat operations)",
            required=False,
            default=0,
        ),
        MCPToolParameter(
            name="output_tokens",
            type="integer",
            description="Estimated output tokens (for chat operations)",
            required=False,
            default=0,
        ),
    ],
    category="credit",
)
async def estimate_credit(
    user_id: int,
    db: AsyncSession,
    operation_type: str,
    model: str | None = None,
    input_tokens: int = 0,
    output_tokens: int = 0,
) -> dict[str, Any]:
    """Estimate credit cost for an operation."""
    service = CreditService(db)

    op_type = OperationType(operation_type)

    if op_type == OperationType.CHAT:
        if not model:
            raise ValueError("Model is required for chat operations")

        cost = await service.calculate_token_cost(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

        return {
            "operation_type": operation_type,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "estimated_cost": str(cost),
        }
    else:
        cost = await service.get_operation_cost(op_type)

        return {
            "operation_type": operation_type,
            "estimated_cost": str(cost),
        }
