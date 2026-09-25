from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from social_hub.domain.entities.social_account import SocialAccount
from social_hub.domain.value_objects.platform_type import PlatformType
from social_hub.domain.value_objects.social_capabilities import SocialCapabilities
from social_hub.shared.types import TenantContext


@dataclass
class ConnectStartResult:
    auth_url: str | None = None
    account: SocialAccount | None = None
    mode: str = "credentials"


@dataclass
class PageOption:
    page_id: str
    name: str
    metadata: dict = field(default_factory=dict)


@dataclass
class MediaItem:
    url: str
    type: str | None = None  # image | video | gif | document


@dataclass
class CreatePostRequest:
    content: str | None = None
    media_items: list[MediaItem] = field(default_factory=list)
    account_ids: list[UUID] = field(default_factory=list)
    publish_now: bool = False
    scheduled_for: str | None = None
    is_draft: bool = False
    timezone: str = "Asia/Tehran"
    platform_specific_data: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)
    external_ref: str | None = None
    title: str | None = None
    price: float | None = None
    currency: str | None = None
    buttons: list[dict] = field(default_factory=list)
    request_id: str | None = None


@dataclass
class PlatformPostResult:
    account_id: UUID
    platform: str
    status: str
    platform_post_url: str | None = None
    platform_message_id: str | None = None
    error: str | None = None


@dataclass
class SocialPostResult:
    post_id: UUID
    status: str
    http_status: int = 201
    platforms: list[PlatformPostResult] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    raw: dict = field(default_factory=dict)


class PlatformAdapter(ABC):
    @property
    @abstractmethod
    def platform(self) -> PlatformType: ...

    @property
    @abstractmethod
    def capabilities(self) -> SocialCapabilities: ...

    @abstractmethod
    async def connect_start(
        self,
        tenant_ctx: TenantContext,
        *,
        redirect_url: str | None = None,
        login_method: str | None = None,
        mode: str | None = None,
        credentials: dict | None = None,
        settings: dict | None = None,
    ) -> ConnectStartResult: ...

    async def connect_list_pages(self, connect_token: str) -> list[PageOption]:
        raise NotImplementedError

    async def connect_select(self, connect_token: str, page_id: str) -> SocialAccount:
        raise NotImplementedError

    @abstractmethod
    async def disconnect(self, account: SocialAccount) -> None: ...

    @abstractmethod
    async def create_post(
        self,
        tenant_ctx: TenantContext,
        account: SocialAccount,
        request: CreatePostRequest,
        credentials: dict | None = None,
    ) -> PlatformPostResult: ...

    async def get_publishing_quota(self, account: SocialAccount, api_key: str) -> dict:
        raise NotImplementedError

    async def test_connection(self, account: SocialAccount, credentials: dict) -> dict:
        return {"ok": True}
