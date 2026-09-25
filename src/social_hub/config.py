from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    app_env: str = "development"
    database_url: str = "postgresql+asyncpg://socialhub:secret@localhost:5432/socialhub"
    redis_url: str = "redis://localhost:6379/0"
    encryption_key: str = ""
    webhook_base_url: str = ""

    # Upstream Instagram provider (internal only — never exposed in public API)
    zernio_api_key: str = ""
    zernio_base_url: str = "https://zernio.com/api"
    zernio_default_profile_id: str = ""
    zernio_media_cdn_base: str = "https://media.zernio.com"
    zernio_webhook_secret: str = ""

    # Public Codenegar URLs
    social_connect_callback_base_url: str = ""
    social_media_relay_base_url: str = ""

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @property
    def connect_callback_base(self) -> str:
        return (self.social_connect_callback_base_url or self.webhook_base_url).rstrip("/")

    @property
    def media_relay_base(self) -> str:
        return (self.social_media_relay_base_url or self.webhook_base_url).rstrip("/")


@lru_cache
def get_settings() -> Settings:
    return Settings()
