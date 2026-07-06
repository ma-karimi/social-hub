from dataclasses import dataclass, field
from uuid import UUID


@dataclass
class PublicationItem:
    id: str
    status: str
    connection_id: str


@dataclass
class PublishResult:
    post_id: str
    publications: list[PublicationItem] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
