"""Credit management API endpoints."""

from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentUser, DbSession, ServiceTokenVerified
from app.schemas.credit import (
    CreditBalanceResponse,
    CreditCheckRequest,
    CreditCheckResponse,
    CreditHistoryResponse,
    CreditTransactionResponse,
    SystemCreditDeductRequest,
    SystemCreditDeductResponse,
    SystemCreditRefundRequest,
    SystemCreditRefundResponse,
)
from app.services.credit import CreditService, InsufficientCreditsError

router = APIRouter(prefix="/credits", tags=["credits"])


@router.get("/balance", response_model=CreditBalanceResponse)
async def get_credit_balance(
    current_user: CurrentUser,
    db: DbSession,
) -> CreditBalanceResponse:
    """Get current user's credit balance."""
    credit_service = CreditService(db)
    balance = await credit_service.get_balance(current_user.id)

    return CreditBalanceResponse(
        gifted_credits=balance["gifted_credits"],
        purchased_credits=balance["purchased_credits"],
        total_credits=balance["total_credits"],
    )


@router.get("/history", response_model=CreditHistoryResponse)
async def get_credit_history(
    current_user: CurrentUser,
    db: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    days: Annotated[int, Query(ge=1, le=365)] = 30,
) -> CreditHistoryResponse:
    """Get current user's credit transaction history."""
    credit_service = CreditService(db)
    result = await credit_service.get_transaction_history(
        user_id=current_user.id,
        page=page,
        page_size=page_size,
        days=days,
    )

    return CreditHistoryResponse(
        transactions=[
            CreditTransactionResponse.model_validate(t)
            for t in result["transactions"]
        ],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
        has_more=result["has_more"],
    )



@router.get("/packages", response_model=list)
async def get_credit_packages(
    db: DbSession,
) -> list:
    """Get available credit packages for purchase."""
    from app.services.stripe import StripeService

    stripe_service = StripeService(db)
    packages = stripe_service.get_packages()
    return [p.model_dump() for p in packages]


@router.post("/recharge")
async def create_recharge_order(
    current_user: CurrentUser,
    db: DbSession,
    package_id: str = Query(..., description="Credit package ID"),
    success_url: str = Query(..., description="URL to redirect after successful payment"),
    cancel_url: str = Query(..., description="URL to redirect if payment is cancelled"),
) -> dict:
    """Create a Stripe checkout session for credit recharge."""
    from app.services.stripe import StripeService

    stripe_service = StripeService(db)

    try:
        result = await stripe_service.create_checkout_session(
            user_id=current_user.id,
            user_email=current_user.email,
            package_id=package_id,
            success_url=success_url,
            cancel_url=cancel_url,
        )

        return {
            "order_id": result["session_id"],
            "checkout_url": result["checkout_url"],
            "package": result["package"].model_dump(),
            "status": "pending",
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create checkout session",
        )



# Internal endpoints (for admin/MCP use only)
# These should be protected by additional authentication in production

@router.get("/config", response_model=dict)
async def get_credit_config(
    current_user: CurrentUser,
    db: DbSession,
) -> dict:
    """Get current credit configuration.
    
    Note: This endpoint is for internal use only.
    In production, add admin role verification.
    """
    credit_service = CreditService(db)
    return await credit_service.get_config_dict()


@router.put("/config", response_model=dict)
async def update_credit_config(
    current_user: CurrentUser,
    db: DbSession,
    gemini_flash_input_rate: Decimal | None = Query(None, ge=0),
    gemini_flash_output_rate: Decimal | None = Query(None, ge=0),
    gemini_pro_input_rate: Decimal | None = Query(None, ge=0),
    gemini_pro_output_rate: Decimal | None = Query(None, ge=0),
    image_generation_rate: Decimal | None = Query(None, ge=0),
    video_generation_rate: Decimal | None = Query(None, ge=0),
    landing_page_rate: Decimal | None = Query(None, ge=0),
    competitor_analysis_rate: Decimal | None = Query(None, ge=0),
    optimization_suggestion_rate: Decimal | None = Query(None, ge=0),
    registration_bonus: Decimal | None = Query(None, ge=0),
) -> dict:
    """Update credit configuration.
    
    Note: This endpoint is for admin use only.
    In production, add admin role verification.
    """
    # TODO: Add admin role verification
    # if not current_user.is_admin:
    #     raise HTTPException(status_code=403, detail="Admin access required")

    credit_service = CreditService(db)

    await credit_service.update_config(
        updated_by=current_user.email,
        gemini_flash_input_rate=gemini_flash_input_rate,
        gemini_flash_output_rate=gemini_flash_output_rate,
        gemini_pro_input_rate=gemini_pro_input_rate,
        gemini_pro_output_rate=gemini_pro_output_rate,
        image_generation_rate=image_generation_rate,
        video_generation_rate=video_generation_rate,
        landing_page_rate=landing_page_rate,
        competitor_analysis_rate=competitor_analysis_rate,
        optimization_suggestion_rate=optimization_suggestion_rate,
        registration_bonus=registration_bonus,
    )

    return await credit_service.get_config_dict()


@router.get("/config/history", response_model=list)
async def get_config_change_history(
    current_user: CurrentUser,
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list:
    """Get credit configuration change history.
    
    Note: This endpoint is for admin use only.
    In production, add admin role verification.
    """
    # TODO: Add admin role verification
    # if not current_user.is_admin:
    #     raise HTTPException(status_code=403, detail="Admin access required")

    credit_service = CreditService(db)
    return await credit_service.get_config_change_history(limit=limit, offset=offset)


# ============================================================================
# System-level Credit API endpoints (for AI Orchestrator)
# These endpoints use service token authentication, not user JWT
# ============================================================================


@router.post("/check", response_model=CreditCheckResponse)
async def check_credits(
    request: CreditCheckRequest,
    _: ServiceTokenVerified,
    db: DbSession,
) -> CreditCheckResponse:
    """Check if user has sufficient credits (system-level).

    This endpoint is called by the AI Orchestrator before consuming operations.
    Authenticated by service token, not user JWT.
    """
    credit_service = CreditService(db)
    balance = await credit_service.get_balance(int(request.user_id))

    available = balance["total_credits"]
    sufficient = available >= request.amount

    return CreditCheckResponse(
        sufficient=sufficient,
        required=request.amount,
        available=available,
    )


@router.post("/deduct", response_model=SystemCreditDeductResponse)
async def deduct_credits(
    request: SystemCreditDeductRequest,
    _: ServiceTokenVerified,
    db: DbSession,
) -> SystemCreditDeductResponse:
    """Deduct credits from user's balance (system-level).

    This endpoint is called by the AI Orchestrator after operations complete.
    Authenticated by service token, not user JWT.
    """
    credit_service = CreditService(db)

    try:
        transaction = await credit_service.deduct_credits(
            user_id=int(request.user_id),
            amount=request.amount,
            operation_type=request.operation_type,
            operation_id=request.operation_id,
            details=request.details,
        )
        await db.commit()

        return SystemCreditDeductResponse(
            success=True,
            transaction_id=transaction.id,
            deducted=transaction.amount,
            from_gifted=transaction.from_gifted,
            from_purchased=transaction.from_purchased,
            balance_after=transaction.balance_after,
        )

    except InsufficientCreditsError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "INSUFFICIENT_CREDITS",
                    "message": "Credit 余额不足",
                    "details": {
                        "required": float(e.required),
                        "available": float(e.available),
                    },
                }
            },
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"code": "INVALID_REQUEST", "message": str(e)}},
        )


@router.post("/refund", response_model=SystemCreditRefundResponse)
async def refund_credits(
    request: SystemCreditRefundRequest,
    _: ServiceTokenVerified,
    db: DbSession,
) -> SystemCreditRefundResponse:
    """Refund credits to user's balance (system-level).

    This endpoint is called by the AI Orchestrator when operations fail.
    Authenticated by service token, not user JWT.
    """
    credit_service = CreditService(db)

    try:
        transaction = await credit_service.refund_credits(
            user_id=int(request.user_id),
            amount=request.amount,
            operation_type=request.operation_type,
            operation_id=request.operation_id,
            reason=request.reason,
        )
        await db.commit()

        return SystemCreditRefundResponse(
            success=True,
            transaction_id=transaction.id,
            refunded=transaction.amount,
            balance_after=transaction.balance_after,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"code": "INVALID_REQUEST", "message": str(e)}},
        )
