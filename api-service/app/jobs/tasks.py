from __future__ import annotations

import logging
from typing import Any

import dramatiq

from app.clients.classifier_client import GrpcClassifierClient
from app.core.config import get_settings
from app.core.database import ApplicationRepository
from app.jobs.broker import redis_broker
from app.services.application_service import ApplicationService


logger = logging.getLogger(__name__)


def _build_service() -> ApplicationService:
    settings = get_settings()
    repository = ApplicationRepository(settings)
    repository.initialize(retries=3, delay_seconds=1.0)
    return ApplicationService(
        classifier_client=GrpcClassifierClient(settings),
        repository=repository,
        settings=settings,
    )


def _mark_started(job_id: str) -> None:
    repository = ApplicationRepository(get_settings())
    repository.initialize(retries=3, delay_seconds=1.0)
    repository.mark_worker_job_started(job_id)


def _mark_completed(job_id: str, result: dict[str, Any]) -> None:
    repository = ApplicationRepository(get_settings())
    repository.initialize(retries=3, delay_seconds=1.0)
    repository.mark_worker_job_completed(job_id, result)


def _mark_failed(job_id: str, error: str) -> None:
    repository = ApplicationRepository(get_settings())
    repository.initialize(retries=3, delay_seconds=1.0)
    repository.mark_worker_job_failed(job_id, error)


@dramatiq.actor(
    broker=redis_broker,
    actor_name="article_import",
    queue_name=get_settings().worker_default_queue,
    max_retries=0,
    time_limit=15 * 60 * 1000,
)
def import_article_job(job_id: str, payload: dict[str, Any]) -> None:
    _mark_started(job_id)
    try:
        service = _build_service()
        result = service.import_article(
            title=payload.get("title"),
            content=payload.get("content"),
            source_url=payload.get("source_url"),
            source=payload.get("source") or "VietnamNet",
            label_hint=payload.get("label_hint"),
            run_inference=bool(payload.get("run_inference", True)),
        )
        _mark_completed(job_id, {"articleId": result["articleId"], "status": result["status"]})
    except Exception as exc:
        logger.exception("Article import job failed: %s", job_id)
        _mark_failed(job_id, str(exc))
        raise


@dramatiq.actor(
    broker=redis_broker,
    actor_name="monitoring_recompute",
    queue_name=get_settings().worker_default_queue,
    max_retries=0,
    time_limit=10 * 60 * 1000,
)
def recompute_monitoring_job(job_id: str, payload: dict[str, Any]) -> None:
    _mark_started(job_id)
    try:
        service = _build_service()
        result = service.recompute_monitoring()
        _mark_completed(
            job_id,
            {
                "snapshotId": result.get("id"),
                "status": result.get("status", "ok"),
                "reason": result.get("reason"),
                "trigger": payload.get("trigger", "manual"),
            },
        )
    except Exception as exc:
        logger.exception("Monitoring recompute job failed: %s", job_id)
        _mark_failed(job_id, str(exc))
        raise
