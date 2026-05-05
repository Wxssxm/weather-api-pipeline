"""Long-lived APScheduler process: triggers `run_ingestion` on a cron schedule."""

from __future__ import annotations

import signal
from typing import NoReturn

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger

from weather_pipeline.config import get_settings
from weather_pipeline.pipeline import run_ingestion


def _job() -> None:
    try:
        report = run_ingestion()
        logger.info("Scheduled run finished: {}", report)
    except Exception:
        logger.exception("Scheduled job raised; will retry at next tick")


def run_scheduler() -> NoReturn:
    settings = get_settings()
    scheduler = BlockingScheduler(timezone="UTC")

    trigger = CronTrigger.from_crontab(
        f"{settings.schedule_cron_minute} {settings.schedule_cron_hour} * * *"
    )
    scheduler.add_job(_job, trigger=trigger, id="ingest", coalesce=True, max_instances=1)

    logger.info(
        "Scheduler starting: cron='{m} {h} * * *', startup={s}",
        m=settings.schedule_cron_minute,
        h=settings.schedule_cron_hour,
        s=settings.ingest_on_startup,
    )

    if settings.ingest_on_startup:
        _job()

    def _shutdown(*_: object) -> None:
        logger.info("Shutdown signal received; stopping scheduler.")
        scheduler.shutdown(wait=False)

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    scheduler.start()
    raise SystemExit(0)
