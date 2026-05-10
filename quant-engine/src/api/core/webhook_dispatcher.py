import httpx
import asyncio
import json
import hmac
import hashlib
from loguru import logger
import duckdb
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent
DB_PATH = BASE_DIR / "quant-engine" / "storage" / "db" / "quant_data.duckdb"

class WebhookDispatcher:
    """
    Phase 12.2: Outbound Webhook Dispatcher.
    Pushes SignalPayload events to client-registered URLs using HMAC SHA-256 signatures asynchronously.
    """
    
    @staticmethod
    def _generate_signature(secret: str, payload_str: str) -> str:
        """Phase 12.1.1: Cryptographic Webhook Signatures (HMAC SHA-256)."""
        return hmac.new(
            secret.encode('utf-8'),
            payload_str.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

    @staticmethod
    async def dispatch_signals_to_clients(signals: list):
        """Asynchronously push signals to all active client webhooks."""
        if not signals:
            return
            
        logger.info(f"Webhook Dispatcher: Preparing to send {len(signals)} signals to clients.")
        
        try:
            con = duckdb.connect(str(DB_PATH), read_only=True)
            webhooks = con.execute("SELECT webhook_id, endpoint_url, hmac_secret FROM client_webhooks WHERE is_active = TRUE").df()
            con.close()
            
            if webhooks.empty:
                logger.info("No active client webhooks registered.")
                return
                
            # Serialize payload once
            payload_data = [s.model_dump() for s in signals] if hasattr(signals[0], 'model_dump') else signals
            payload_str = json.dumps(payload_data)
            
            tasks = []
            async with httpx.AsyncClient(timeout=10.0) as client:
                for _, row in webhooks.iterrows():
                    url = row['endpoint_url']
                    secret = row['hmac_secret']
                    webhook_id = row['webhook_id']
                    
                    signature = WebhookDispatcher._generate_signature(secret, payload_str)
                    
                    headers = {
                        "Content-Type": "application/json",
                        "X-Swarm-Signature": signature
                    }
                    
                    # Create the async task
                    task = WebhookDispatcher._send_webhook(client, url, payload_str, headers, webhook_id)
                    tasks.append(task)
                    
                # Run all webhook POST requests concurrently without blocking the main loop
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                success_count = sum(1 for r in results if r is True)
                logger.success(f"Webhook Dispatcher: Successfully delivered {success_count}/{len(tasks)} webhooks.")
                
        except Exception as e:
            logger.error(f"Critical error in webhook dispatcher: {e}")

    @staticmethod
    async def _send_webhook(client: httpx.AsyncClient, url: str, payload: str, headers: dict, webhook_id: str) -> bool:
        """Individual webhook HTTP POST."""
        try:
            response = await client.post(url, content=payload, headers=headers)
            response.raise_for_status()
            return True
        except Exception as e:
            logger.warning(f"Webhook delivery failed for {webhook_id} at {url}: {e}")
            return False
