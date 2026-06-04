import logging

from app.db import SessionLocal
from app.services.fdm_service import FdmService

logger = logging.getLogger(__name__)


def run_fdm_poll() -> None:
    db = SessionLocal()
    try:
        count = FdmService(db).poll_new_imports()
        logger.info("FDM poll complete: %s operations ingested", count)
    except Exception:
        logger.exception("FDM poll failed")
        db.rollback()
    finally:
        db.close()
