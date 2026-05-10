from pydantic import BaseModel, HttpUrl
from typing import List

class CheckoutRequest(BaseModel):
    tier: str  # 'PRO' or 'INSTITUTIONAL'

class CheckoutResponse(BaseModel):
    checkout_url: HttpUrl

class ClientWebhookCreate(BaseModel):
    endpoint_url: HttpUrl

class ClientWebhookResponse(BaseModel):
    webhook_id: str
    endpoint_url: HttpUrl
    hmac_secret: str  # Only returned ONCE upon creation
    is_active: bool
