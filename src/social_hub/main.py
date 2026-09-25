from contextlib import asynccontextmanager
from copy import deepcopy

import structlog
from fastapi import FastAPI, Request
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import JSONResponse

from social_hub.api.i18n import error_body, error_from_exception, resolve_locale
from social_hub.api.middleware import LoggingMiddleware
from social_hub.api.v1.router import api_router
from social_hub.config import get_settings
from social_hub.domain.error_codes import ErrorCode
from social_hub.domain.exceptions import SocialHubError

logger = structlog.get_logger(__name__)

APP_TITLE_EN = "Codenegar Social API"
APP_TITLE_FA = "API اجتماعی کدنگر"
APP_DESC_EN = (
    "Multi-tenant social publishing and inbox API. "
    "Instagram, Telegram, Bale, and Eitaa under one surface."
)
APP_DESC_FA = (
    "API چندمستأجری انتشار و صندوق پیام شبکه‌های اجتماعی. "
    "اینستاگرام، تلگرام، بله و ایتا در یک سطح واحد."
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from social_hub.container import build_container

    settings = get_settings()
    container = await build_container(settings)
    app.state.container = container
    logger.info("socialhub_started", env=settings.app_env)
    yield
    logger.info("socialhub_stopped")


def _strip_provider_brand(obj):
    """Ensure OpenAPI payload never mentions the upstream provider brand."""
    if isinstance(obj, dict):
        return {k: _strip_provider_brand(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_strip_provider_brand(v) for v in obj]
    if isinstance(obj, str):
        lowered = obj.lower()
        if "zernio" in lowered:
            return obj.replace("Zernio", "Codenegar").replace("zernio", "codenegar")
        return obj
    return obj


def create_app(lifespan_override=None) -> FastAPI:
    app = FastAPI(
        title=APP_TITLE_EN,
        description=APP_DESC_EN,
        version="0.2.0",
        lifespan=lifespan_override or lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    app.add_middleware(LoggingMiddleware)
    app.include_router(api_router, prefix="/api/v1")

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.get("/openapi.json", include_in_schema=False)
    async def openapi_en():
        schema = app.openapi()
        schema["info"]["title"] = APP_TITLE_EN
        schema["info"]["description"] = APP_DESC_EN
        return _strip_provider_brand(schema)

    @app.get("/openapi.fa.json", include_in_schema=False)
    async def openapi_fa():
        schema = deepcopy(app.openapi())
        schema["info"]["title"] = APP_TITLE_FA
        schema["info"]["description"] = APP_DESC_FA
        # Translate common path summaries if present
        for path_item in schema.get("paths", {}).values():
            for op in path_item.values():
                if not isinstance(op, dict):
                    continue
                if "summary" in op:
                    op["summary"] = _fa_summary(op.get("summary", ""))
                if "description" in op and op["description"]:
                    op["description"] = _fa_desc(op["description"])
        return _strip_provider_brand(schema)

    @app.get("/docs", include_in_schema=False)
    async def docs_en():
        return get_swagger_ui_html(openapi_url="/openapi.json", title=APP_TITLE_EN)

    @app.get("/docs/fa", include_in_schema=False)
    async def docs_fa():
        return get_swagger_ui_html(openapi_url="/openapi.fa.json", title=APP_TITLE_FA)

    @app.exception_handler(SocialHubError)
    async def social_hub_error_handler(request: Request, exc: SocialHubError):
        locale = resolve_locale(request.headers.get("accept-language"))
        status_code, body = error_from_exception(exc, locale=locale)
        return JSONResponse(status_code=status_code, content=body)

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.exception("unhandled_error", path=request.url.path)
        locale = resolve_locale(request.headers.get("accept-language"))
        return JSONResponse(
            status_code=500,
            content=error_body(ErrorCode.INTERNAL_ERROR, locale=locale),
        )

    return app


def _fa_summary(text: str) -> str:
    mapping = {
        "Connect Account": "اتصال اکانت",
        "List Accounts": "لیست اکانت‌ها",
        "Create Post": "ساخت پست",
        "Media Presign": "پیش‌امضای رسانه",
    }
    return mapping.get(text, text)


def _fa_desc(text: str) -> str:
    if "Requires Facebook Login connection" in text:
        return text.replace(
            "Requires Facebook Login connection",
            "نیازمند اتصال با Facebook Login",
        )
    return text


app = create_app()
