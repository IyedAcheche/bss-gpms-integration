import logging

from app.db import SessionLocal
from app.services.hums_service import HumsService

logger = logging.getLogger(__name__)


def run_hums_poll() -> None:
    db = SessionLocal()
    try:
        count = HumsService(db).poll_and_store()
        logger.info("HUMS poll complete: %s assets updated", count)
    except Exception:
        logger.exception("HUMS poll failed")
        db.rollback()
    finally:
        db.close()
