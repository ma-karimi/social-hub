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

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()
