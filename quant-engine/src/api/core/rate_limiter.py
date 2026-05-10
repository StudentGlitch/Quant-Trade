from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from fastapi import Request

# Phase 11.3: API Gateway token bucket logic
# 60 requests per minute per IP or API key context
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])
