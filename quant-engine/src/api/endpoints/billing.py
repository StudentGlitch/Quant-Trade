from fastapi import APIRouter, Depends, HTTPException, Request
from loguru import logger
import duckdb
from pathlib import Path

from .compliance_schemas import CheckoutRequest, CheckoutResponse
from .auth_router import get_current_active_user, get_duckdb_conn
from ..core.stripe_client import StripeClient
from ..core.audit_logger import AuditLogger

router = APIRouter()
stripe_client = StripeClient()

@router.post("/billing/checkout", response_model=CheckoutResponse)
async def create_checkout(request: Request, checkout_req: CheckoutRequest, current_user: dict = Depends(get_current_active_user), con: duckdb.DuckDBPyConnection = Depends(get_duckdb_conn)):
    """Phase 12.1: Generate Stripe Checkout Session."""
    if con is None:
        raise HTTPException(status_code=503, detail="Database connection failed")
        
    try:
        user_id = current_user['user_id']
        email = current_user['email']
        tier = checkout_req.tier.upper()
        
        return_url = f"{request.base_url}investor/dashboard"
        checkout_url = stripe_client.create_checkout_session(user_id, email, tier, return_url)
        
        await AuditLogger.log_action(con, "STRIPE_CHECKOUT_INITIATED", user_id=user_id, resource_id=tier, request=request)
        
        return CheckoutResponse(checkout_url=checkout_url)
    except Exception as e:
        logger.error(f"Checkout generation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to create checkout session")

@router.post("/billing/portal")
async def create_portal(request: Request, current_user: dict = Depends(get_current_active_user), con: duckdb.DuckDBPyConnection = Depends(get_duckdb_conn)):
    """Phase 12.1: Generate Stripe Customer Portal Session."""
    if con is None:
        raise HTTPException(status_code=503, detail="Database connection failed")
        
    try:
        user_id = current_user['user_id']
        
        # Get stripe customer ID from DB
        row = con.execute("SELECT stripe_customer_id FROM users WHERE user_id = ?", [user_id]).fetchone()
        if not row or not row[0]:
            raise HTTPException(status_code=400, detail="No active subscription found. Please subscribe first.")
            
        customer_id = row[0]
        return_url = f"{request.base_url}investor/dashboard"
        
        portal_url = stripe_client.create_customer_portal(customer_id, return_url)
        
        await AuditLogger.log_action(con, "STRIPE_PORTAL_ACCESSED", user_id=user_id, resource_id=customer_id, request=request)
        
        return {"portal_url": portal_url}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Portal generation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to create portal session")
