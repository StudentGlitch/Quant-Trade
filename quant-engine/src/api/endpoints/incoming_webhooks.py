import stripe
from fastapi import APIRouter, Request, HTTPException, Depends
from loguru import logger
import os
import duckdb

from .auth_router import get_duckdb_conn

router = APIRouter()
endpoint_secret = os.getenv('STRIPE_WEBHOOK_SECRET', 'whsec_test_mock')

@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request, con: duckdb.DuckDBPyConnection = Depends(get_duckdb_conn)):
    """Phase 12.1: Listen to Stripe events (e.g., checkout.session.completed)."""
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')

    try:
        # Phase 12.1.2: Stripe Webhook Verification
        if endpoint_secret == 'whsec_test_mock':
            # For testing with mock events
            import json
            event = stripe.Event.construct_from(json.loads(payload), stripe.api_key)
        else:
            event = stripe.Webhook.construct_event(
                payload, sig_header, endpoint_secret
            )
    except ValueError as e:
        logger.error("Invalid payload in Stripe webhook")
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        logger.error("Invalid signature in Stripe webhook")
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Handle the event
    if con:
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            user_id = session.get('client_reference_id')
            customer_id = session.get('customer')
            
            # Assuming tier is passed in metadata or derived from line items in a real app
            # For this mock, we assume upgrade to PRO
            tier = 'PRO' 
            
            logger.info(f"Stripe Webhook: Checkout complete for user {user_id}. Upgrading to {tier}.")
            
            con.execute("""
                UPDATE users 
                SET stripe_customer_id = ?, subscription_tier = ?, subscription_status = 'ACTIVE'
                WHERE user_id = ?
            """, [customer_id, tier, user_id])

        elif event['type'] == 'customer.subscription.deleted':
            subscription = event['data']['object']
            customer_id = subscription.get('customer')
            
            logger.info(f"Stripe Webhook: Subscription deleted for customer {customer_id}.")
            
            con.execute("""
                UPDATE users 
                SET subscription_tier = 'FREE', subscription_status = 'INACTIVE'
                WHERE stripe_customer_id = ?
            """, [customer_id])

    return {"status": "success"}
