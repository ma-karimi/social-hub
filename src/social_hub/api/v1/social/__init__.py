from fastapi import APIRouter

from social_hub.api.v1.social import accounts, instagram_extra, media, posts, webhooks

social_router = APIRouter()
social_router.include_router(accounts.router)
social_router.include_router(posts.router)
social_router.include_router(media.router)
social_router.include_router(instagram_extra.router)
social_router.include_router(webhooks.router)
