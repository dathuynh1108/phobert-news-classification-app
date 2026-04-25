from __future__ import annotations

import logging
import queue
import secrets
import signal
import threading
import time

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from redis import Redis
from redis.exceptions import RedisError

from app.core.config import get_settings
from app.core.database import ApplicationRepository
from app.jobs.tasks import recompute_monitoring_job


logger = logging.getLogger(__name__)
shutdown_queue: queue.Queue[bool] = queue.Queue()


def _enqueue_scheduled_monitoring() -> None:
    settings = get_settings()
    repository = ApplicationRepository(settings)
    repository.initialize(retries=3, delay_seconds=1.0)
    payload = {"trigger": "cron"}
    job_id = f"job-scheduled-monitoring-{int(time.time())}-{secrets.token_hex(3)}"
    job = repository.create_worker_job(
        job_id=job_id,
        job_type="monitoring_recompute",
        payload=payload,
        created_by="scheduler",
    )
    recompute_monitoring_job.send(job["jobId"], payload)
    logger.info("Queued scheduled monitoring job %s", job["jobId"])


def _scheduler_loop() -> None:
    settings = get_settings()
    redis_client = Redis.from_url(settings.redis_url)
    lock = redis_client.lock("vnn-worker-scheduler", timeout=90, blocking=False, thread_local=False)
    scheduler: BackgroundScheduler | None = None
    heartbeat_stop = threading.Event()

    try:
        if not lock.acquire(blocking=False):
            logger.info("Scheduler lock is held by another worker")
            return

        def heartbeat() -> None:
            while not heartbeat_stop.wait(30):
                try:
                    lock.extend(90, replace_ttl=True)
                except RedisError:
                    logger.exception("Failed to extend scheduler lock")

        threading.Thread(target=heartbeat, daemon=True).start()

        scheduler = BackgroundScheduler()
        scheduler.add_job(
            _enqueue_scheduled_monitoring,
            CronTrigger.from_crontab(settings.drift_monitoring_cron),
            id="monitoring_recompute",
            replace_existing=True,
            max_instances=1,
        )
        scheduler.start()
        logger.info("Worker scheduler started with drift cron %s", settings.drift_monitoring_cron)
        shutdown_queue.get(block=True)
    except Exception:
        logger.exception("Worker scheduler failed")
    finally:
        heartbeat_stop.set()
        if scheduler:
            scheduler.shutdown(wait=False)
        try:
            if lock.owned():
                lock.release()
        except RedisError:
            logger.exception("Failed to release scheduler lock")


def _signal_handler(signum: int, frame: object) -> None:
    logger.info("Received signal %s, stopping scheduler", signum)
    shutdown_queue.put(True)


def start_scheduler() -> threading.Thread:
    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)
    scheduler_thread = threading.Thread(target=_scheduler_loop, daemon=True)
    scheduler_thread.start()
    return scheduler_thread
