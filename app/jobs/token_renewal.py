import logging

from app.db import SessionLocal
from app.services.token_manager import TokenManager

logger = logging.getLogger(__name__)


def run_token_renewal() -> None:
    db = SessionLocal()
    try:
        manager = TokenManager(db)
        if manager.should_renew_proactively():
            manager.get_valid_token(force_refresh=True)
            logger.info("GPMS JWT renewed proactively")
    except Exception:
        logger.exception("GPMS token renewal failed")
        db.rollback()
    finally:
        db.close()
