from fastapi import APIRouter

from social_hub.api.v1 import tenants
from social_hub.api.v1.social import social_router

api_router = APIRouter()

api_router.include_router(tenants.router, prefix="/tenants", tags=["tenants"])
api_router.include_router(social_router, prefix="/social")
