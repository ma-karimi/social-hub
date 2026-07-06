from dataclasses import dataclass


@dataclass
class DeleteResult:
    post_id: str
    delete_enqueued: int
