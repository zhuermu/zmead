"""Webhook endpoints for external services."""

import logging

from fastapi import APIRouter, Header, HTTPException, Request, status

from app.api.deps import DbSession
from app.services.stripe import StripeService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    db: DbSession,
    stripe_signature: str = Header(..., alias="Stripe-Signature"),
) -> dict:
    """Handle Stripe webhook events.
    
    This endpoint receives webhook events from Stripe for payment processing.
    Events handled:
    - checkout.session.completed: Credit purchase completed
    - payment_intent.payment_failed: Payment failed
    """
    # Get raw body for signature verification
    payload = await request.body()

    # Verify webhook signature
    event = StripeService.verify_webhook_signature(payload, stripe_signature)

    if not event:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid webhook signature",
        )

    event_type = event.get("type")
    event_data = event.get("data", {}).get("object", {})

    logger.info(f"Received Stripe webhook: {event_type}")

    stripe_service = StripeService(db)

    try:
        if event_type == "checkout.session.completed":
            # Payment successful, add credits
            success = await stripe_service.handle_checkout_completed(event_data)
            if not success:
                logger.error(f"Failed to process checkout completion: {event.get('id')}")

        elif event_type == "payment_intent.payment_failed":
            # Payment failed
            await stripe_service.handle_payment_failed(event_data)

        else:
            logger.debug(f"Unhandled Stripe event type: {event_type}")

        return {"status": "ok"}

    except Exception as e:
        logger.exception(f"Error processing Stripe webhook: {e}")
        # Return 200 to prevent Stripe from retrying
        # Log the error for investigation
        return {"status": "error", "message": str(e)}
