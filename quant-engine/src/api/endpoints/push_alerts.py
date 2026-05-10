from fastapi import APIRouter, Request, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict
from loguru import logger
import duckdb
import uuid
from pathlib import Path

from .auth_router import get_current_active_user, get_duckdb_conn

router = APIRouter()

class PushSubscription(BaseModel):
    endpoint: str
    keys: Dict[str, str]

@router.post("/push/subscribe")
async def subscribe_push(sub: PushSubscription, request: Request, current_user: dict = Depends(get_current_active_user), con: duckdb.DuckDBPyConnection = Depends(get_duckdb_conn)):
    """Phase 13.2: Register a VAPID device."""
    if con is None:
        raise HTTPException(status_code=503, detail="Database connection failed")
        
    try:
        user_id = current_user['user_id']
        device_id = f"dev_{uuid.uuid4().hex}"
        
        # Determine device type via User-Agent roughly
        ua = request.headers.get("user-agent", "").lower()
        device_type = "MOBILE" if "mobi" in ua else "DESKTOP"
        
        import json
        sub_json = json.dumps(sub.model_dump())
        
        con.execute("""
            INSERT OR REPLACE INTO push_device_registry (device_id, user_id, subscription_info, device_type)
            VALUES (?, ?, ?, ?)
        """, [device_id, user_id, sub_json, device_type])
        
        logger.info(f"VAPID Push: Registered new {device_type} device for user {user_id}")
        return {"status": "success", "device_id": device_id}
        
    except Exception as e:
        logger.error(f"Failed to register push device: {e}")
        raise HTTPException(status_code=500, detail="Failed to register device")

@router.post("/push/unsubscribe")
async def unsubscribe_push(device_id: str, current_user: dict = Depends(get_current_active_user), con: duckdb.DuckDBPyConnection = Depends(get_duckdb_conn)):
    """Phase 13.2: Unregister a VAPID device."""
    if con is None:
        raise HTTPException(status_code=503, detail="Database connection failed")
        
    try:
        user_id = current_user['user_id']
        con.execute("DELETE FROM push_device_registry WHERE device_id = ? AND user_id = ?", [device_id, user_id])
        logger.info(f"VAPID Push: Unregistered device {device_id} for user {user_id}")
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Failed to unregister push device: {e}")
        raise HTTPException(status_code=500, detail="Failed to unregister device")
