from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4


@dataclass
class ConnectSession:
    id: UUID
    our_connect_token: str
    upstream_connect_token: str | None
    tenant_id: UUID
    platform: str
    consumer_redirect_url: str
    login_method: str
    mode: str
    expires_at: datetime
    metadata: dict
    created_at: datetime | None = None

    @classmethod
    def create(
        cls,
        tenant_id: UUID,
        platform: str,
        consumer_redirect_url: str,
        *,
        login_method: str = "instagram_login",
        mode: str = "headless",
        upstream_connect_token: str | None = None,
        ttl_minutes: int = 15,
        metadata: dict | None = None,
    ) -> "ConnectSession":
        now = datetime.now(timezone.utc)
        return cls(
            id=uuid4(),
            our_connect_token=uuid4().hex,
            upstream_connect_token=upstream_connect_token,
            tenant_id=tenant_id,
            platform=platform,
            consumer_redirect_url=consumer_redirect_url,
            login_method=login_method,
            mode=mode,
            expires_at=now + timedelta(minutes=ttl_minutes),
            metadata=metadata or {},
            created_at=now,
        )

    @property
    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) >= self.expires_at
