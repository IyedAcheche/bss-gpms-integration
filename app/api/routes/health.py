from urllib.parse import urlparse

from fastapi import APIRouter

from app.config import get_settings
from app.db import check_db_connection

router = APIRouter(tags=["health"])


def _db_label(database_url: str) -> str:
    parsed = urlparse(database_url)
    host = parsed.hostname or "localhost"
    port = f":{parsed.port}" if parsed.port else ""
    db = (parsed.path or "").lstrip("/") or "?"
    return f"postgresql@{host}{port}/{db}"


@router.get("/health", summary="Health check")
def health() -> dict[str, str]:
    """Returns API status and PostgreSQL connectivity (no credentials)."""
    settings = get_settings()
    db_ok = False
    try:
        db_ok = check_db_connection()
    except Exception:
        pass
    return {
        "status": "ok" if db_ok else "degraded",
        "database": _db_label(settings.database_url),
        "db_connected": "yes" if db_ok else "no",
    }
