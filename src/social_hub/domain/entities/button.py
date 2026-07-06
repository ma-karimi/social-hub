from dataclasses import dataclass, field
from uuid import UUID, uuid4

from social_hub.domain.value_objects.button_action import ButtonAction


@dataclass
class Button:
    id: UUID
    post_id: UUID
    action_type: ButtonAction
    label: str
    payload: dict = field(default_factory=dict)
    sort_order: int = 0
    short_id: str | None = None

    @classmethod
    def create(
        cls,
        post_id: UUID,
        action_type: ButtonAction,
        label: str,
        payload: dict | None = None,
        sort_order: int = 0,
    ) -> "Button":
        return cls(
            id=uuid4(),
            post_id=post_id,
            action_type=action_type,
            label=label,
            payload=payload or {},
            sort_order=sort_order,
        )
