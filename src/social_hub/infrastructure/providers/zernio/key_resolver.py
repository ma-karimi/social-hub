from dataclasses import dataclass
from uuid import UUID

from social_hub.config import Settings
from social_hub.infrastructure.db.repositories.social_aux_repos import (
    SQLAlchemyProviderCredentialRepo,
)
from social_hub.infrastructure.encryption.credential_encryptor import FernetEncryptor


@dataclass(frozen=True)
class ProviderCredentials:
    api_key: str
    base_url: str
    profile_id: str
    media_cdn_base: str


class ProviderKeyResolver:
    """Resolves upstream API credentials: tenant override → env defaults."""

    def __init__(
        self,
        settings: Settings,
        encryptor: FernetEncryptor,
        credential_repo: SQLAlchemyProviderCredentialRepo,
    ) -> None:
        self._settings = settings
        self._encryptor = encryptor
        self._repo = credential_repo

    async def resolve(self, tenant_id: UUID) -> ProviderCredentials:
        override = await self._repo.get(tenant_id, "zernio")
        if override is not None:
            data = self._encryptor.decrypt(bytes(override.api_key_encrypted))
            return ProviderCredentials(
                api_key=data.get("api_key") or data.get("key") or "",
                base_url=self._settings.zernio_base_url.rstrip("/"),
                profile_id=override.profile_id or self._settings.zernio_default_profile_id,
                media_cdn_base=self._settings.zernio_media_cdn_base.rstrip("/"),
            )
        return ProviderCredentials(
            api_key=self._settings.zernio_api_key,
            base_url=self._settings.zernio_base_url.rstrip("/"),
            profile_id=self._settings.zernio_default_profile_id,
            media_cdn_base=self._settings.zernio_media_cdn_base.rstrip("/"),
        )
