from fastapi import APIRouter

from social_hub.api.v1 import posts, connections, tenants
from social_hub.api.v1.webhooks.router import webhooks_router

api_router = APIRouter()

api_router.include_router(posts.router, prefix="/posts", tags=["posts"])
api_router.include_router(connections.router, prefix="/connections", tags=["connections"])
api_router.include_router(tenants.router, prefix="/tenants", tags=["tenants"])
api_router.include_router(webhooks_router, prefix="/webhooks", tags=["webhooks"])
