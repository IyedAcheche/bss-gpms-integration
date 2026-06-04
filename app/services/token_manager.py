from __future__ import annotations

import threading
from datetime import datetime, timedelta

import jwt
from sqlalchemy.orm import Session

_renew_lock = threading.Lock()

from app.config import Settings, get_settings
from app.models.auth import GpmsAuthToken
from app.services.gpms_client import GpmsApiError, GpmsClient
from app.time_utils import UTC, ensure_utc, utc_now


def _expiry_from_jwt(token: str, fallback_days: int) -> datetime:
    try:
        payload = jwt.decode(token, options={"verify_signature": False})
        exp = payload.get("exp")
        if exp:
            return datetime.fromtimestamp(exp, tz=UTC)
    except jwt.PyJWTError:
        pass
    return utc_now() + timedelta(days=fallback_days)


class TokenManager:
    def __init__(self, db: Session, settings: Settings | None = None):
        self.db = db
        self.settings = settings or get_settings()

    def get_valid_token(self, *, force_refresh: bool = False) -> str:
        # Fast path: token is valid, no lock needed.
        row = self.db.get(GpmsAuthToken, 1)
        now = utc_now()
        if (
            not force_refresh
            and row
            and ensure_utc(row.expires_at) > now + timedelta(minutes=5)
        ):
            return row.token

        # Slow path: acquire process-wide lock so only one thread renews at a time.
        with _renew_lock:
            # Re-read from DB — another thread may have renewed while we waited.
            if row is not None:
                self.db.expire(row)
            row = self.db.get(GpmsAuthToken, 1)
            now = utc_now()
            if (
                not force_refresh
                and row
                and ensure_utc(row.expires_at) > now + timedelta(minutes=5)
            ):
                return row.token
            return self._renew(row)

    def _renew(self, row: GpmsAuthToken | None) -> str:
        token = GpmsClient.login(self.settings)
        expires_at = _expiry_from_jwt(token, self.settings.gpms_token_renewal_days)
        now = utc_now()
        if row is None:
            row = GpmsAuthToken(id=1, token=token, expires_at=expires_at, updated_at=now)
            self.db.add(row)
        else:
            row.token = token
            row.expires_at = expires_at
            row.updated_at = now
        self.db.commit()
        return token

    def ensure_token_on_startup(self) -> None:
        try:
            self.get_valid_token()
        except GpmsApiError:
            # Credentials may be unset during local scaffold; jobs will log failures.
            pass

    def should_renew_proactively(self) -> bool:
        row = self.db.get(GpmsAuthToken, 1)
        if not row:
            return True
        renew_before = timedelta(days=self.settings.gpms_token_renewal_days)
        updated = ensure_utc(row.updated_at)
        if updated is None:
            return True
        return updated <= utc_now() - renew_before
