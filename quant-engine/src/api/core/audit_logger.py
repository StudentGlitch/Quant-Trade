import duckdb
from loguru import logger
import uuid
from typing import Optional
from fastapi import Request

class AuditLogger:
    """
    Phase 12.3: SOC-2 Audit Logging Middleware.
    Records every sensitive action into an immutable DuckDB audit_logs table.
    """
    
    @staticmethod
    def _get_client_ip(request: Request) -> str:
        if not request:
            return "system"
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0]
        return request.client.host if request.client else "unknown"

    @staticmethod
    async def log_action(
        con: duckdb.DuckDBPyConnection, 
        action: str, 
        user_id: Optional[str] = None, 
        resource_id: Optional[str] = None,
        request: Request = None
    ):
        """Asynchronously write to the audit_logs table."""
        if con is None:
            logger.warning(f"Audit log skipped (no db connection): {action} by {user_id}")
            return
            
        ip_address = AuditLogger._get_client_ip(request)
        log_id = f"evt_{uuid.uuid4().hex}"
        
        try:
            # We use an async fire-and-forget mechanism if this is called within an async endpoint,
            # or just execute sequentially. For simplicity here, we execute synchronously.
            # DuckDB allows concurrent readers but only one writer, so connection pooling/queues
            # might be needed in high-scale prod.
            con.execute("""
                INSERT INTO audit_logs (log_id, user_id, action, ip_address, resource_id, timestamp)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, [log_id, user_id, action, ip_address, resource_id])
            logger.debug(f"Audit Logged: {action} [{user_id}]")
        except Exception as e:
            logger.error(f"CRITICAL: Failed to write audit log: {e}")
