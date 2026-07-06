from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from social_hub.api.middleware import LoggingMiddleware
from social_hub.api.v1.router import api_router
from social_hub.config import get_settings

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from social_hub.container import build_container

    settings = get_settings()
    container = await build_container(settings)
    app.state.container = container
    logger.info("socialhub_started", env=settings.app_env)
    yield
    logger.info("socialhub_stopped")


def create_app(lifespan_override=None) -> FastAPI:
    app = FastAPI(
        title="SocialHub",
        description="Multi-Tenant Social Publishing Platform",
        version="0.1.0",
        lifespan=lifespan_override or lifespan,
    )

    app.add_middleware(LoggingMiddleware)
    app.include_router(api_router, prefix="/api/v1")

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.exception("unhandled_error", path=request.url.path)
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})

    return app


app = create_app()
