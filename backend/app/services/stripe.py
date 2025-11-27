"""Stripe service for payment processing."""

import logging
from decimal import Decimal
from typing import Any

import stripe
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.schemas.credit import TransactionType
from app.schemas.stripe import CreditPackage
from app.services.credit import CreditService

logger = logging.getLogger(__name__)

# Initialize Stripe
stripe.api_key = settings.stripe_api_key

# Default credit packages (can be overridden by database config)
DEFAULT_PACKAGES: list[CreditPackage] = [
    CreditPackage(
        id="package_experience",
        name="体验包",
        price_cents=9900,  # ¥99
        credits=1000,
        discount_percent=0,
        description="适合初次体验",
    ),
    CreditPackage(
        id="package_standard",
        name="标准包",
        price_cents=29900,  # ¥299
        credits=3000,
        discount_percent=10,
        description="9折优惠",
    ),
    CreditPackage(
        id="package_professional",
        name="专业包",
        price_cents=99900,  # ¥999
        credits=10000,
        discount_percent=20,
        description="8折优惠",
    ),
    CreditPackage(
        id="package_enterprise",
        name="企业包",
        price_cents=299900,  # ¥2999
        credits=30000,
        discount_percent=30,
        description="7折优惠",
    ),
]


class StripeService:
    """Service for Stripe payment operations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.credit_service = CreditService(db)

    def get_packages(self) -> list[CreditPackage]:
        """Get available credit packages.
        
        Returns:
            List of available credit packages
        """
        # TODO: Load from database config if available
        return DEFAULT_PACKAGES

    def get_package_by_id(self, package_id: str) -> CreditPackage | None:
        """Get a specific credit package by ID.
        
        Args:
            package_id: Package ID
            
        Returns:
            CreditPackage if found, None otherwise
        """
        packages = self.get_packages()
        for package in packages:
            if package.id == package_id:
                return package
        return None

    async def create_checkout_session(
        self,
        user_id: int,
        user_email: str,
        package_id: str,
        success_url: str,
        cancel_url: str,
    ) -> dict[str, Any]:
        """Create a Stripe checkout session for credit purchase.
        
        Args:
            user_id: User ID
            user_email: User email
            package_id: Credit package ID
            success_url: URL to redirect after successful payment
            cancel_url: URL to redirect if payment is cancelled
            
        Returns:
            Dictionary with session_id and checkout_url
            
        Raises:
            ValueError: If package not found
        """
        package = self.get_package_by_id(package_id)
        if not package:
            raise ValueError(f"Package not found: {package_id}")

        try:
            session = stripe.checkout.Session.create(
                payment_method_types=["card", "alipay", "wechat_pay"],
                line_items=[
                    {
                        "price_data": {
                            "currency": "cny",
                            "product_data": {
                                "name": f"AAE Credits - {package.name}",
                                "description": f"{package.credits} Credits",
                            },
                            "unit_amount": package.price_cents,
                        },
                        "quantity": 1,
                    }
                ],
                mode="payment",
                success_url=success_url,
                cancel_url=cancel_url,
                customer_email=user_email,
                metadata={
                    "user_id": str(user_id),
                    "package_id": package_id,
                    "credits": str(package.credits),
                },
                payment_intent_data={
                    "metadata": {
                        "user_id": str(user_id),
                        "package_id": package_id,
                        "credits": str(package.credits),
                    }
                },
            )

            return {
                "session_id": session.id,
                "checkout_url": session.url,
                "package": package,
            }
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating checkout session: {e}")
            raise

    async def handle_checkout_completed(
        self,
        session: dict[str, Any],
    ) -> bool:
        """Handle successful checkout completion.
        
        Args:
            session: Stripe checkout session data
            
        Returns:
            True if credits were added successfully
        """
        metadata = session.get("metadata", {})
        user_id = metadata.get("user_id")
        package_id = metadata.get("package_id")
        credits_str = metadata.get("credits")

        if not all([user_id, package_id, credits_str]):
            logger.error(f"Missing metadata in checkout session: {metadata}")
            return False

        try:
            user_id = int(user_id)
            credits = int(credits_str)
        except ValueError:
            logger.error(f"Invalid metadata values: user_id={user_id}, credits={credits_str}")
            return False

        package = self.get_package_by_id(package_id)

        # Add credits to user account
        await self.credit_service.add_credits(
            user_id=user_id,
            amount=Decimal(credits),
            transaction_type=TransactionType.RECHARGE,
            details={
                "stripe_session_id": session.get("id"),
                "package_id": package_id,
                "package_name": package.name if package else package_id,
                "amount_paid": session.get("amount_total"),
                "currency": session.get("currency"),
            },
        )

        logger.info(f"Added {credits} credits to user {user_id} from package {package_id}")
        return True

    async def handle_payment_failed(
        self,
        payment_intent: dict[str, Any],
    ) -> None:
        """Handle failed payment.
        
        Args:
            payment_intent: Stripe payment intent data
        """
        metadata = payment_intent.get("metadata", {})
        user_id = metadata.get("user_id")
        package_id = metadata.get("package_id")

        logger.warning(
            f"Payment failed for user {user_id}, package {package_id}: "
            f"{payment_intent.get('last_payment_error', {}).get('message', 'Unknown error')}"
        )

        # TODO: Send notification to user about failed payment

    @staticmethod
    def verify_webhook_signature(
        payload: bytes,
        signature: str,
    ) -> dict[str, Any] | None:
        """Verify Stripe webhook signature and return event data.
        
        Args:
            payload: Raw request body
            signature: Stripe signature header
            
        Returns:
            Event data if valid, None otherwise
        """
        try:
            event = stripe.Webhook.construct_event(
                payload,
                signature,
                settings.stripe_webhook_secret,
            )
            return event
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Invalid Stripe webhook signature: {e}")
            return None
        except ValueError as e:
            logger.error(f"Invalid Stripe webhook payload: {e}")
            return None
