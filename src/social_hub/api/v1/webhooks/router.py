from fastapi import APIRouter

from social_hub.api.v1.webhooks import bale, telegram

webhooks_router = APIRouter()
webhooks_router.include_router(telegram.router, prefix="/telegram")
webhooks_router.include_router(bale.router, prefix="/bale")
