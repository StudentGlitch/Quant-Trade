import os
import stripe
from loguru import logger
from fastapi import HTTPException

class StripeClient:
    """
    Phase 12.1: Stripe SDK wrapper & secret management.
    """
    
    def __init__(self):
        # We assume standard naming convention for Stripe API keys
        self.api_key = os.getenv("STRIPE_SECRET_KEY", "sk_test_mock123")
        stripe.api_key = self.api_key
        
        # Mock product IDs for testing if live are not provided
        self.products = {
            "PRO": os.getenv("STRIPE_PRICE_PRO", "price_mock_pro"),
            "INSTITUTIONAL": os.getenv("STRIPE_PRICE_INST", "price_mock_inst")
        }

    def create_checkout_session(self, user_id: str, email: str, tier: str, return_url: str):
        """Create a Stripe Checkout Session for subscription upgrades."""
        if tier not in self.products:
            raise ValueError(f"Invalid subscription tier: {tier}")
            
        logger.info(f"Stripe: Creating checkout session for {email} ({tier})")
        
        # If mock key, return a mock URL
        if self.api_key.startswith("sk_test_mock"):
            return f"https://mock.stripe.com/checkout?user={user_id}&tier={tier}"
            
        try:
            session = stripe.checkout.Session.create(
                customer_email=email,
                payment_method_types=['card'],
                line_items=[{
                    'price': self.products[tier],
                    'quantity': 1,
                }],
                mode='subscription',
                success_url=f"{return_url}?session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=return_url,
                client_reference_id=user_id,
            )
            return session.url
        except Exception as e:
            logger.error(f"Stripe Checkout failed: {e}")
            raise HTTPException(status_code=500, detail="Payment gateway error")

    def create_customer_portal(self, customer_id: str, return_url: str):
        """Create a Stripe Customer Portal session."""
        logger.info(f"Stripe: Creating portal for customer {customer_id}")
        
        if self.api_key.startswith("sk_test_mock"):
            return f"https://mock.stripe.com/portal?customer={customer_id}"
            
        try:
            session = stripe.billing_portal.Session.create(
                customer=customer_id,
                return_url=return_url,
            )
            return session.url
        except Exception as e:
            logger.error(f"Stripe Portal failed: {e}")
            raise HTTPException(status_code=500, detail="Billing portal error")
