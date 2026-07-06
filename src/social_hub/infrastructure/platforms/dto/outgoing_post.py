from dataclasses import dataclass, field

from social_hub.domain.value_objects.media_ref import MediaRef
from social_hub.infrastructure.platforms.dto.outgoing_button import OutgoingButton


@dataclass
class OutgoingPost:
    text: str
    media: list[MediaRef] = field(default_factory=list)
    # Rows of buttons (platform drivers decide how to lay them out)
    buttons: list[list[OutgoingButton]] = field(default_factory=list)
