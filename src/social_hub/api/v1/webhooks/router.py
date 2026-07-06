from fastapi import APIRouter

from social_hub.api.v1.webhooks import telegram

webhooks_router = APIRouter()
webhooks_router.include_router(telegram.router, prefix="/telegram")
