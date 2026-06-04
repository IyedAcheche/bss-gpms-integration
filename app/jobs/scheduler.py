from __future__ import annotations

import logging
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler

from app.config import get_settings
from app.jobs.fdm_poll import run_fdm_poll
from app.jobs.hums_poll import run_hums_poll
from app.jobs.token_renewal import run_token_renewal

logger = logging.getLogger(__name__)
_scheduler: BackgroundScheduler | None = None


def start_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler is not None:
        return _scheduler

    settings = get_settings()
    scheduler = BackgroundScheduler(timezone="UTC")

    scheduler.add_job(
        run_hums_poll,
        "interval",
        seconds=settings.hums_poll_interval_seconds,
        id="hums_poll",
        replace_existing=True,
    )
    scheduler.add_job(
        run_fdm_poll,
        "interval",
        seconds=settings.fdm_poll_interval_seconds,
        id="fdm_poll",
        replace_existing=True,
        next_run_time=datetime.now(tz=timezone.utc),
    )
    scheduler.add_job(
        run_token_renewal,
        "interval",
        days=settings.gpms_token_renewal_days,
        id="token_renewal",
        replace_existing=True,
    )

    scheduler.start()
    _scheduler = scheduler
    logger.info("Background scheduler started")
    return scheduler


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
