from __future__ import annotations

from app.core.config import get_settings
from app.jobs.scheduler import start_scheduler
from app.jobs.tasks import import_article_job, recompute_monitoring_job


if get_settings().enable_worker_scheduler:
    start_scheduler()


__all__ = ["import_article_job", "recompute_monitoring_job"]
