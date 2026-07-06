from dataclasses import dataclass, field
from uuid import UUID, uuid4
from datetime import datetime


@dataclass
class Tenant:
    id: UUID
    name: str
    api_key_hash: str
    is_active: bool = True
    settings: dict = field(default_factory=dict)
    created_at: datetime | None = None

    @classmethod
    def create(cls, name: str, api_key_hash: str, settings: dict | None = None) -> "Tenant":
        return cls(
            id=uuid4(),
            name=name,
            api_key_hash=api_key_hash,
            settings=settings or {},
        )

    @property
    def webhook_callback_url(self) -> str | None:
        return self.settings.get("webhook_callback_url")

    @property
    def locale(self) -> str:
        return self.settings.get("locale", "fa")
