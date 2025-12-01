"""Credit schemas for API requests and responses."""

from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field


class TransactionType(str, Enum):
    """Credit transaction types."""
    DEDUCT = "deduct"
    REFUND = "refund"
    RECHARGE = "recharge"
    GIFT = "gift"


class OperationType(str, Enum):
    """Operation types that consume credits."""
    CHAT = "chat"
    IMAGE_GENERATION = "image_generation"
    VIDEO_GENERATION = "video_generation"
    LANDING_PAGE = "landing_page"
    COMPETITOR_ANALYSIS = "competitor_analysis"
    OPTIMIZATION_SUGGESTION = "optimization_suggestion"


class CreditBalanceResponse(BaseModel):
    """Credit balance response schema."""

    gifted_credits: Decimal
    purchased_credits: Decimal
    total_credits: Decimal

    model_config = {"from_attributes": True}


class CreditDeductRequest(BaseModel):
    """Request to deduct credits."""

    amount: Decimal = Field(..., gt=0, description="Amount of credits to deduct")
    operation_type: OperationType
    operation_id: str | None = Field(None, description="Unique ID for the operation")
    details: dict = Field(default_factory=dict, description="Additional details like model, tokens")


class CreditRefundRequest(BaseModel):
    """Request to refund credits."""

    amount: Decimal = Field(..., gt=0, description="Amount of credits to refund")
    operation_type: OperationType
    operation_id: str | None = Field(None, description="Original operation ID")
    reason: str | None = Field(None, description="Reason for refund")


class CreditTransactionResponse(BaseModel):
    """Credit transaction response schema."""

    id: int
    user_id: int
    type: str
    amount: Decimal
    from_gifted: Decimal
    from_purchased: Decimal
    balance_after: Decimal
    operation_type: str | None
    operation_id: str | None
    details: dict
    created_at: datetime

    model_config = {"from_attributes": True}


class CreditHistoryResponse(BaseModel):
    """Credit history response with pagination."""

    transactions: list[CreditTransactionResponse]
    total: int
    page: int
    page_size: int
    has_more: bool



class CreditConfigResponse(BaseModel):
    """Credit configuration response schema."""

    id: int
    gemini_flash_input_rate: float
    gemini_flash_output_rate: float
    gemini_pro_input_rate: float
    gemini_pro_output_rate: float
    image_generation_rate: float
    video_generation_rate: float
    landing_page_rate: float
    competitor_analysis_rate: float
    optimization_suggestion_rate: float
    registration_bonus: float
    packages: dict
    updated_at: str | None
    updated_by: str | None


class CreditConfigUpdateRequest(BaseModel):
    """Request to update credit configuration (admin only)."""

    gemini_flash_input_rate: Decimal | None = Field(None, ge=0)
    gemini_flash_output_rate: Decimal | None = Field(None, ge=0)
    gemini_pro_input_rate: Decimal | None = Field(None, ge=0)
    gemini_pro_output_rate: Decimal | None = Field(None, ge=0)
    image_generation_rate: Decimal | None = Field(None, ge=0)
    video_generation_rate: Decimal | None = Field(None, ge=0)
    landing_page_rate: Decimal | None = Field(None, ge=0)
    competitor_analysis_rate: Decimal | None = Field(None, ge=0)
    optimization_suggestion_rate: Decimal | None = Field(None, ge=0)
    registration_bonus: Decimal | None = Field(None, ge=0)
    packages: dict | None = None


# ============================================================================
# System-level Credit API schemas (for AI Orchestrator)
# These are used by internal service-to-service communication
# ============================================================================


class CreditCheckRequest(BaseModel):
    """Request to check if user has sufficient credits (system-level)."""

    user_id: str = Field(..., description="User ID")
    amount: Decimal = Field(..., gt=0, description="Amount of credits required")
    operation_type: str | None = Field(None, description="Type of operation")


class CreditCheckResponse(BaseModel):
    """Response for credit check (system-level)."""

    sufficient: bool = Field(..., description="Whether user has sufficient credits")
    required: Decimal = Field(..., description="Credits required")
    available: Decimal = Field(..., description="Credits available")


class SystemCreditDeductRequest(BaseModel):
    """Request to deduct credits (system-level)."""

    user_id: str = Field(..., description="User ID")
    amount: Decimal = Field(..., gt=0, description="Amount of credits to deduct")
    operation_type: str = Field(..., description="Type of operation")
    operation_id: str | None = Field(None, description="Unique operation ID")
    details: dict = Field(default_factory=dict, description="Additional details")


class SystemCreditDeductResponse(BaseModel):
    """Response for credit deduction (system-level)."""

    success: bool
    transaction_id: int | None = None
    deducted: Decimal
    from_gifted: Decimal
    from_purchased: Decimal
    balance_after: Decimal


class SystemCreditRefundRequest(BaseModel):
    """Request to refund credits (system-level)."""

    user_id: str = Field(..., description="User ID")
    amount: Decimal = Field(..., gt=0, description="Amount of credits to refund")
    operation_type: str = Field(..., description="Type of operation")
    operation_id: str | None = Field(None, description="Original operation ID")
    reason: str | None = Field(None, description="Reason for refund")


class SystemCreditRefundResponse(BaseModel):
    """Response for credit refund (system-level)."""

    success: bool
    transaction_id: int | None = None
    refunded: Decimal
    balance_after: Decimal
