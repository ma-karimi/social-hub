"""Arq worker settings and startup/shutdown hooks."""
import os

from arq.connections import RedisSettings

from social_hub.infrastructure.queue.jobs.delete_job import delete_job
from social_hub.infrastructure.queue.jobs.edit_job import edit_job
from social_hub.infrastructure.queue.jobs.process_interaction_job import process_interaction_job
from social_hub.infrastructure.queue.jobs.publish_job import publish_job


async def startup(ctx: dict) -> None:
    from social_hub.config import get_settings
    from social_hub.container import build_container

    settings = get_settings()
    ctx["container"] = await build_container(settings)


async def shutdown(ctx: dict) -> None:
    container = ctx.get("container")
    if container and hasattr(container, "arq_redis"):
        await container.arq_redis.aclose()


class WorkerSettings:
    functions = [publish_job, edit_job, delete_job, process_interaction_job]
    on_startup = startup
    on_shutdown = shutdown
    max_tries = 3
    job_timeout = 60
    # Read REDIS_URL at class-definition time from env (set before worker starts)
    redis_settings = RedisSettings.from_dsn(
        os.getenv("REDIS_URL", "redis://localhost:6379/0")
    )
