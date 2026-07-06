from dataclasses import dataclass, field


@dataclass
class EditResult:
    post_id: str
    enqueued: bool
    warnings: list[str] = field(default_factory=list)
