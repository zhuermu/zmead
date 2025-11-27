"""Stripe-related schemas for API requests and responses."""

from enum import Enum

from pydantic import BaseModel, Field


class CreditPackage(BaseModel):
    """Credit package definition."""

    id: str
    name: str
    price_cents: int  # Price in cents (e.g., 9900 = ¥99)
    credits: int
    discount_percent: int = 0
    description: str | None = None


class RechargeOrderStatus(str, Enum):
    """Recharge order status."""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CreateRechargeOrderRequest(BaseModel):
    """Request to create a recharge order."""

    package_id: str = Field(..., description="ID of the credit package to purchase")
    success_url: str = Field(..., description="URL to redirect after successful payment")
    cancel_url: str = Field(..., description="URL to redirect if payment is cancelled")


class RechargeOrderResponse(BaseModel):
    """Response for recharge order creation."""

    order_id: str
    checkout_url: str
    package: CreditPackage
    status: RechargeOrderStatus


class CreditPackagesResponse(BaseModel):
    """Response listing available credit packages."""

    packages: list[CreditPackage]


class StripeWebhookEvent(BaseModel):
    """Stripe webhook event data."""

    id: str
    type: str
    data: dict
