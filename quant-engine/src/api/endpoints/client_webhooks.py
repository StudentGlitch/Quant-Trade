from fastapi import APIRouter, Depends, HTTPException, Request
from loguru import logger
import duckdb
import uuid
import secrets
from pathlib import Path
from typing import List

from .compliance_schemas import ClientWebhookCreate, ClientWebhookResponse
from .auth_router import get_current_active_user, get_duckdb_conn
from ..core.audit_logger import AuditLogger

router = APIRouter()

@router.post("/webhooks", response_model=ClientWebhookResponse)
async def register_webhook(request: Request, webhook_req: ClientWebhookCreate, current_user: dict = Depends(get_current_active_user), con: duckdb.DuckDBPyConnection = Depends(get_duckdb_conn)):
    """Phase 12.4: Register a new webhook endpoint."""
    if con is None:
        raise HTTPException(status_code=503, detail="Database connection failed")
        
    try:
        # Schema ensure
        con.execute("""
            CREATE TABLE IF NOT EXISTS client_webhooks (
                webhook_id VARCHAR PRIMARY KEY,
                user_id VARCHAR REFERENCES users(user_id),
                endpoint_url TEXT NOT NULL,
                hmac_secret VARCHAR NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        user_id = current_user['user_id']
        webhook_id = f"wh_{uuid.uuid4().hex}"
        endpoint_url = str(webhook_req.endpoint_url)
        
        # Section 7.1: Secret Generation
        hmac_secret = secrets.token_urlsafe(32)
        
        con.execute("""
            INSERT INTO client_webhooks (webhook_id, user_id, endpoint_url, hmac_secret)
            VALUES (?, ?, ?, ?)
        """, [webhook_id, user_id, endpoint_url, hmac_secret])
        
        await AuditLogger.log_action(con, "WEBHOOK_REGISTERED", user_id=user_id, resource_id=webhook_id, request=request)
        
        return ClientWebhookResponse(
            webhook_id=webhook_id,
            endpoint_url=endpoint_url,
            hmac_secret=hmac_secret, # Returned ONCE
            is_active=True
        )
    except Exception as e:
        logger.error(f"Webhook registration failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to register webhook")

@router.get("/webhooks", response_model=List[ClientWebhookResponse])
def list_webhooks(current_user: dict = Depends(get_current_active_user), con: duckdb.DuckDBPyConnection = Depends(get_duckdb_conn)):
    if con is None:
        raise HTTPException(status_code=503, detail="Database connection failed")
        
    user_id = current_user['user_id']
    try:
        df = con.execute("SELECT webhook_id, endpoint_url, is_active FROM client_webhooks WHERE user_id = ?", [user_id]).df()
        res = []
        for _, row in df.iterrows():
            res.append(ClientWebhookResponse(
                webhook_id=row['webhook_id'],
                endpoint_url=row['endpoint_url'],
                hmac_secret="HIDDEN",
                is_active=bool(row['is_active'])
            ))
        return res
    except Exception as e:
        logger.error(f"Failed to list webhooks: {e}")
        # Could be table doesn't exist yet
        return []
