"""
Stripe Webhook Routes

Handles Stripe webhook events for subscription management,
payment processing, and credit pack purchases.
"""

import json
from datetime import datetime, timezone
from typing import Optional

import stripe
from fastapi import APIRouter, HTTPException, Header, Request

from backend.config import config
from backend.database.users import UserService
from backend.database.credits import CreditService

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


# =============================================================================
# Initialize Stripe
# =============================================================================

def get_stripe():
    """Initialize Stripe with API key."""
    if not config.STRIPE_SECRET_KEY:
        raise HTTPException(
            status_code=503,
            detail="Stripe not configured"
        )
    stripe.api_key = config.STRIPE_SECRET_KEY
    return stripe


# =============================================================================
# Webhook Handler
# =============================================================================

@router.post("/stripe")
async def handle_stripe_webhook(
    request: Request,
    stripe_signature: Optional[str] = Header(None, alias="Stripe-Signature")
):
    """
    Handle incoming Stripe webhook events.

    Processes subscription lifecycle events and payment completions.
    """
    if not config.stripe_configured:
        raise HTTPException(
            status_code=503,
            detail="Stripe webhooks not configured"
        )

    if not stripe_signature:
        raise HTTPException(
            status_code=400,
            detail="Missing Stripe-Signature header"
        )

    # Get raw body for signature verification
    body = await request.body()

    try:
        # Verify webhook signature
        event = stripe.Webhook.construct_event(
            body,
            stripe_signature,
            config.STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid payload: {e}")
    except stripe.error.SignatureVerificationError as e:
        raise HTTPException(status_code=400, detail=f"Invalid signature: {e}")

    # Handle the event
    event_type = event["type"]
    data = event["data"]["object"]

    handlers = {
        "checkout.session.completed": handle_checkout_completed,
        "invoice.paid": handle_invoice_paid,
        "invoice.payment_failed": handle_invoice_payment_failed,
        "customer.subscription.updated": handle_subscription_updated,
        "customer.subscription.deleted": handle_subscription_deleted,
        "payment_intent.succeeded": handle_payment_intent_succeeded,
    }

    handler = handlers.get(event_type)
    if handler:
        try:
            await handler(data)
        except Exception as e:
            # Log error but return 200 to prevent Stripe retries for handling errors
            print(f"Error handling {event_type}: {e}")
            # In production, you'd want proper logging here
            return {"status": "error", "message": str(e)}

    return {"status": "success", "event_type": event_type}


# =============================================================================
# Event Handlers
# =============================================================================

async def handle_checkout_completed(session: dict):
    """
    Handle successful checkout session.

    This is called when a user completes checkout for:
    - New subscription
    - Credit pack purchase
    """
    user_service = UserService()
    credit_service = CreditService()

    customer_id = session.get("customer")
    customer_email = session.get("customer_email") or session.get("customer_details", {}).get("email")
    mode = session.get("mode")  # 'subscription' or 'payment'
    metadata = session.get("metadata", {})

    # Find user by email
    user = await user_service.get_by_email(customer_email)
    if not user:
        print(f"Warning: No user found for email {customer_email}")
        return

    user_id = user["id"]

    # Link Stripe customer to user if not already linked
    if not user.get("stripe_customer_id"):
        await user_service.update(user_id, {"stripe_customer_id": customer_id})

    if mode == "subscription":
        # New subscription checkout
        subscription_id = session.get("subscription")

        # Get subscription details from Stripe
        get_stripe()
        subscription = stripe.Subscription.retrieve(subscription_id)

        # Determine tier from price ID
        price_id = subscription["items"]["data"][0]["price"]["id"]
        tier = "annual" if price_id == config.STRIPE_PRICE_ANNUAL else "monthly"

        # Update user subscription
        await user_service.update_subscription(
            user_id,
            status="active",
            tier=tier,
            stripe_customer_id=customer_id,
            stripe_subscription_id=subscription_id,
            current_period_start=datetime.fromtimestamp(
                subscription["current_period_start"], tz=timezone.utc
            ),
            current_period_end=datetime.fromtimestamp(
                subscription["current_period_end"], tz=timezone.utc
            ),
        )

        # Add initial credits (15 for first month)
        # Note: Trial credits stack with subscription credits
        await credit_service.add_subscription_credits(
            user_id,
            tier=tier,
            stripe_invoice_id=session.get("invoice"),
        )

    elif mode == "payment":
        # One-time payment (credit pack)
        pack_type = metadata.get("pack_type")  # '5', '10', or '20'
        if pack_type:
            pack_size = int(pack_type)
            amount_paid = session.get("amount_total", 0)

            await credit_service.add_credit_pack(
                user_id,
                pack_size=pack_size,
                stripe_payment_id=session.get("payment_intent"),
                amount_paid_cents=amount_paid,
            )


async def handle_invoice_paid(invoice: dict):
    """
    Handle successful invoice payment.

    This is called for recurring subscription payments.
    Refreshes the user's monthly credits.
    """
    user_service = UserService()
    credit_service = CreditService()

    customer_id = invoice.get("customer")
    subscription_id = invoice.get("subscription")

    # Skip if this is a one-time payment (no subscription)
    if not subscription_id:
        return

    # Find user by Stripe customer ID
    user = await user_service.get_by_stripe_customer(customer_id)
    if not user:
        print(f"Warning: No user found for Stripe customer {customer_id}")
        return

    user_id = user["id"]
    tier = user.get("subscription_tier", "monthly")

    # Get subscription details for period end
    get_stripe()
    subscription = stripe.Subscription.retrieve(subscription_id)

    # Update subscription period
    await user_service.update_subscription(
        user_id,
        status="active",
        current_period_start=datetime.fromtimestamp(
            subscription["current_period_start"], tz=timezone.utc
        ),
        current_period_end=datetime.fromtimestamp(
            subscription["current_period_end"], tz=timezone.utc
        ),
    )

    # Add monthly credits (for both monthly and annual tiers)
    # Annual gets 15/month drip, not 180 upfront
    await credit_service.add_subscription_credits(
        user_id,
        tier=tier,
        stripe_invoice_id=invoice.get("id"),
    )


async def handle_invoice_payment_failed(invoice: dict):
    """
    Handle failed invoice payment.

    Updates user status to past_due.
    """
    user_service = UserService()

    customer_id = invoice.get("customer")
    subscription_id = invoice.get("subscription")

    if not subscription_id:
        return

    user = await user_service.get_by_stripe_customer(customer_id)
    if not user:
        return

    await user_service.update_subscription(
        user["id"],
        status="past_due",
    )


async def handle_subscription_updated(subscription: dict):
    """
    Handle subscription updates.

    This handles upgrades, downgrades, and cancellation scheduling.
    """
    user_service = UserService()

    customer_id = subscription.get("customer")

    user = await user_service.get_by_stripe_customer(customer_id)
    if not user:
        return

    user_id = user["id"]

    # Map Stripe status to our status
    stripe_status = subscription.get("status")
    status_map = {
        "active": "active",
        "past_due": "past_due",
        "canceled": "cancelled",
        "unpaid": "past_due",
        "trialing": "trial",  # If we ever add Stripe trials
    }
    status = status_map.get(stripe_status, stripe_status)

    # Check if cancellation is scheduled
    cancel_at_period_end = subscription.get("cancel_at_period_end", False)

    # Determine tier from price
    price_id = subscription["items"]["data"][0]["price"]["id"]
    tier = "annual" if price_id == config.STRIPE_PRICE_ANNUAL else "monthly"

    await user_service.update_subscription(
        user_id,
        status=status,
        tier=tier,
        cancel_at_period_end=cancel_at_period_end,
        current_period_end=datetime.fromtimestamp(
            subscription["current_period_end"], tz=timezone.utc
        ),
    )


async def handle_subscription_deleted(subscription: dict):
    """
    Handle subscription cancellation/deletion.

    User keeps credits for 30 days, then they expire.
    """
    user_service = UserService()

    customer_id = subscription.get("customer")

    user = await user_service.get_by_stripe_customer(customer_id)
    if not user:
        return

    await user_service.update_subscription(
        user["id"],
        status="cancelled",
        cancel_at_period_end=False,  # Already cancelled
    )

    # Note: Credits remain but will expire after 30 days
    # This should be handled by a background job


async def handle_payment_intent_succeeded(payment_intent: dict):
    """
    Handle successful one-time payment.

    This is a backup handler for credit pack purchases.
    The main handling happens in checkout.session.completed.
    """
    # Most handling done in checkout.session.completed
    # This is here for edge cases where we need to handle the payment directly
    pass


# =============================================================================
# Checkout Session Creation
# =============================================================================

@router.post("/create-checkout-session")
async def create_checkout_session(request: Request):
    """
    Create a Stripe checkout session for subscription or credit pack.
    """
    if not config.stripe_configured:
        raise HTTPException(
            status_code=503,
            detail="Stripe not configured"
        )

    body = await request.json()
    price_id = body.get("price_id")
    user_email = body.get("email")
    mode = body.get("mode", "subscription")  # 'subscription' or 'payment'
    success_url = body.get("success_url", f"{config.APP_BASE_URL}/dashboard?success=true")
    cancel_url = body.get("cancel_url", f"{config.APP_BASE_URL}/pricing?cancelled=true")

    if not price_id:
        raise HTTPException(status_code=400, detail="price_id is required")

    try:
        get_stripe()

        # Determine metadata for credit packs
        metadata = {}
        if mode == "payment":
            # Credit pack purchase
            if price_id == config.STRIPE_PRICE_CREDITS_5:
                metadata["pack_type"] = "5"
            elif price_id == config.STRIPE_PRICE_CREDITS_10:
                metadata["pack_type"] = "10"
            elif price_id == config.STRIPE_PRICE_CREDITS_20:
                metadata["pack_type"] = "20"

        session_params = {
            "mode": mode,
            "success_url": success_url,
            "cancel_url": cancel_url,
            "line_items": [{"price": price_id, "quantity": 1}],
            "metadata": metadata,
        }

        if user_email:
            session_params["customer_email"] = user_email

        if mode == "subscription":
            session_params["subscription_data"] = {
                "metadata": metadata
            }

        session = stripe.checkout.Session.create(**session_params)

        return {"checkout_url": session.url, "session_id": session.id}

    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/create-billing-portal")
async def create_billing_portal(request: Request):
    """
    Create a Stripe billing portal session for subscription management.
    """
    if not config.stripe_configured:
        raise HTTPException(
            status_code=503,
            detail="Stripe not configured"
        )

    body = await request.json()
    customer_id = body.get("customer_id")
    return_url = body.get("return_url", f"{config.APP_BASE_URL}/dashboard")

    if not customer_id:
        raise HTTPException(status_code=400, detail="customer_id is required")

    try:
        get_stripe()

        session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url,
        )

        return {"portal_url": session.url}

    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# Pricing Info
# =============================================================================

@router.get("/pricing")
async def get_pricing():
    """
    Get current pricing information.
    """
    return {
        "subscription": {
            "monthly": {
                "price": 999,  # cents
                "price_display": "$9.99",
                "credits": 15,
                "price_id": config.STRIPE_PRICE_MONTHLY,
            },
            "annual": {
                "price": 9900,  # cents
                "price_display": "$99",
                "credits": 180,  # 15/month for 12 months
                "price_id": config.STRIPE_PRICE_ANNUAL,
                "savings": "2 months free",
            },
        },
        "credit_packs": CreditService.get_credit_packs(),
        "free_trial": {
            "credits": 10,
            "requires_card": False,
        },
    }
