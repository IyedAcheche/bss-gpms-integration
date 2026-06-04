"""HTTP client for GPMS Foresight API.

Used by background polls and manual FDM ingest. Production paths use per-asset endpoints
(assets, operations, newimports, exportstates). get_fleets() / iter_assets() are helpers only.
"""

from __future__ import annotations

from typing import Any

import httpx

from app.config import Settings
from app.services.gpms_types import GpmsAsset, GpmsFleet, GpmsOperation


class GpmsApiError(Exception):
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class GpmsClient:
    def __init__(self, settings: Settings, token: str):
        self._base = settings.gpms_base_url.rstrip("/")
        self._token = token
        self._client = httpx.Client(
            base_url=self._base,
            headers={"Authorization": f"Bearer {token}"},
            timeout=120.0,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> GpmsClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    @staticmethod
    def login(settings: Settings) -> str:
        if not settings.gpms_email or not settings.gpms_password:
            raise GpmsApiError("GPMS_EMAIL and GPMS_PASSWORD must be configured")
        with httpx.Client(base_url=settings.gpms_base_url.rstrip("/"), timeout=30.0) as client:
            response = client.post(
                "/auth/user",
                json={"email": settings.gpms_email, "password": settings.gpms_password},
            )
        if response.status_code != 200:
            raise GpmsApiError(
                f"GPMS login failed: {response.status_code} {response.text}",
                response.status_code,
            )
        data = response.json()
        token = data.get("token")
        if not token:
            raise GpmsApiError("GPMS login response missing token")
        return token

    def _get(self, path: str, **params: Any) -> Any:
        response = self._client.get(path, params=params or None)
        if response.status_code >= 400:
            raise GpmsApiError(
                f"GPMS GET {path} failed: {response.status_code} {response.text}",
                response.status_code,
            )
        if not response.content:
            return None
        return response.json()

    def get_fleets(self) -> list[GpmsFleet]:
        raw = self._get("/user/fleets")
        if not isinstance(raw, list):
            return []
        return [GpmsFleet.model_validate(f) for f in raw]

    def iter_assets(self) -> list[GpmsAsset]:
        assets: list[GpmsAsset] = []
        for fleet in self.get_fleets():
            assets.extend(fleet.assets)
        return assets

    def get_asset(self, asset_id: int) -> GpmsAsset:
        raw = self._get(f"/user/assets/{asset_id}")
        return GpmsAsset.model_validate(raw)

    def get_operations(self, asset_id: int, limit: int = 100) -> list[GpmsOperation]:
        raw = self._get(f"/user/assets/{asset_id}/operations", limit=limit)
        if not isinstance(raw, list):
            return []
        return [GpmsOperation.model_validate(op) for op in raw]

    def get_operation(self, asset_id: int, operation_id: int) -> GpmsOperation | None:
        try:
            raw = self._get(f"/user/assets/{asset_id}/operations/{operation_id}")
        except GpmsApiError as exc:
            if exc.status_code == 404:
                return None
            raise
        if not raw:
            return None
        return GpmsOperation.model_validate(raw)

    def get_new_imports(self, asset_id: int, start: str) -> list[int]:
        raw = self._get(f"/user/assets/{asset_id}/newimports", start=start)
        if not isinstance(raw, list):
            return []
        return [int(x) for x in raw]

    def export_states_csv(self, asset_id: int, operation_id: int) -> bytes:
        response = self._client.get(
            f"/user/assets/{asset_id}/exportstates/{operation_id}",
        )
        if response.status_code >= 400:
            raise GpmsApiError(
                f"GPMS exportstates failed: {response.status_code} {response.text}",
                response.status_code,
            )
        return response.content
