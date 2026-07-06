from dataclasses import dataclass

from social_hub.domain.value_objects.media_ref import MediaRef
from social_hub.domain.value_objects.platform_type import PlatformType


@dataclass
class ResolvedMedia:
    source: str  # URL (pass-through) or could be bytes in future
    mime_type: str
    sort_order: int


class MediaResolver:
    """
    Decides how to present media to each platform.
    Phase 1: URL pass-through for all platforms.
    Future: download + re-upload for platforms that require it.
    """

    def resolve(
        self,
        media_refs: list[MediaRef],
        platform_type: PlatformType,
    ) -> list[ResolvedMedia]:
        return [
            ResolvedMedia(
                source=ref.url,
                mime_type=ref.mime_type,
                sort_order=ref.sort_order,
            )
            for ref in sorted(media_refs, key=lambda r: r.sort_order)
        ]
