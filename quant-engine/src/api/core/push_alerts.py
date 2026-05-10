import os
from pywebpush import webpush, WebPushException
from loguru import logger
import duckdb
from pathlib import Path
import json

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent
DB_PATH = BASE_DIR / "quant-engine" / "storage" / "db" / "quant_data.duckdb"

class VAPIDPushService:
    """
    Phase 13.2: VAPID Push Backend Cryptography.
    """
    def __init__(self):
        self.public_key = os.getenv("VAPID_PUBLIC_KEY")
        self.private_key = os.getenv("VAPID_PRIVATE_KEY")
        self.claims = {
            "sub": "mailto:admin@fund.com"
        }
        
    def _init_ledger(self, con):
        con.execute("""
            CREATE TABLE IF NOT EXISTS push_device_registry (
                device_id VARCHAR PRIMARY KEY,
                user_id VARCHAR,
                subscription_info JSON NOT NULL,
                device_type VARCHAR,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

    def send_kill_switch_alert(self, reason: str):
        """Blast High-Priority notification to all Admin devices."""
        if not self.public_key or not self.private_key:
            logger.warning("VAPID keys not configured. Skipping push notification.")
            return
            
        logger.info(f"VAPID Push: Sending Kill Switch Alert ({reason}) to all admins.")
        
        try:
            con = duckdb.connect(str(DB_PATH))
            self._init_ledger(con)
            
            # Assume we just send to all registered devices for now, 
            # in a real system we'd filter by role='ADMIN' via a JOIN with users
            devices = con.execute("SELECT subscription_info FROM push_device_registry").df()
            con.close()
            
            if devices.empty:
                return
                
            payload = json.dumps({
                "title": "🚨 KILL SWITCH ENGAGED",
                "body": f"The CIO Agent has liquidated the portfolio. Reason: {reason}",
                "url": "/command"
            })
            
            for _, row in devices.iterrows():
                try:
                    sub_info = json.loads(row['subscription_info'])
                    webpush(
                        subscription_info=sub_info,
                        data=payload,
                        vapid_private_key=self.private_key,
                        vapid_claims=self.claims
                    )
                except WebPushException as ex:
                    logger.error(f"Push failed: {repr(ex)}")
                except Exception as e:
                    logger.error(f"Push formatting error: {e}")
                    
        except Exception as e:
            logger.error(f"Failed to query push registry: {e}")

    def send_medic_alert(self, message: str):
        """Phase 15: Notify the CIO of new Medic branches."""
        if not self.public_key or not self.private_key:
            logger.warning("VAPID keys not configured. Skipping push notification.")
            return
            
        logger.info(f"VAPID Push: Sending Medic Alert ({message}) to all admins.")
        
        try:
            con = duckdb.connect(str(DB_PATH))
            self._init_ledger(con)
            
            # Assume we just send to all registered devices for now
            devices = con.execute("SELECT subscription_info FROM push_device_registry").df()
            con.close()
            
            if devices.empty:
                return
                
            payload = json.dumps({
                "title": "🛠️ Code Medic Optimization",
                "body": message,
                "url": "/system-health"
            })
            
            for _, row in devices.iterrows():
                try:
                    sub_info = json.loads(row['subscription_info'])
                    webpush(
                        subscription_info=sub_info,
                        data=payload,
                        vapid_private_key=self.private_key,
                        vapid_claims=self.claims
                    )
                except WebPushException as ex:
                    logger.error(f"Push failed: {repr(ex)}")
                except Exception as e:
                    logger.error(f"Push formatting error: {e}")
                    
        except Exception as e:
            logger.error(f"Failed to query push registry for medic alert: {e}")
