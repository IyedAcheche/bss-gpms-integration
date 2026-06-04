from __future__ import annotations

import logging
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.customer import Customer
from app.models.hums import HumsStatusCurrent, HumsStatusSnapshot
from app.models.mapping import GpmsAssetMapping
from app.schemas.events import CriticalEvent
from app.schemas.hums import HumsAircraftStatus
from app.services.gpms_client import GpmsApiError, GpmsClient
from app.services.gpms_types import GpmsAsset
from app.services.mapping_service import MappingService
from app.services.token_manager import TokenManager
from app.time_utils import ensure_utc, utc_now

logger = logging.getLogger(__name__)


def _portal_url(asset_id: int) -> str | None:
    template = get_settings().gpms_portal_asset_url
    if not template:
        return None
    return template.format(asset_id=asset_id)


def _status_or_none(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    return text if text else None


class HumsService:
    def __init__(self, db: Session):
        self.db = db
        self.mappings = MappingService(db)

    def poll_and_store(self) -> int:
        mapped_ids = self.mappings.get_active_gpms_asset_ids()
        if not mapped_ids:
            logger.warning("HUMS poll skipped: no active mappings")
            return 0

        token = TokenManager(self.db).get_valid_token()
        updated = 0
        with GpmsClient(get_settings(), token) as client:
            for gpms_asset_id in mapped_ids:
                try:
                    asset = client.get_asset(gpms_asset_id)
                    self._upsert_asset(asset)
                    self._update_mapping_name(gpms_asset_id, asset.asset_name)
                    updated += 1
                except GpmsApiError:
                    logger.exception(
                        "HUMS poll failed for mapped asset %s", gpms_asset_id
                    )
        self.db.commit()
        return updated

    def _update_mapping_name(self, gpms_asset_id: int, asset_name: str | None) -> None:
        if not asset_name:
            return
        row = self.db.scalar(
            select(GpmsAssetMapping).where(
                GpmsAssetMapping.gpms_asset_id == gpms_asset_id
            )
        )
        if row is not None:
            row.gpms_asset_name = asset_name

    def _upsert_asset(self, asset: GpmsAsset) -> None:
        now = utc_now()
        mdstatus = _status_or_none(asset.mdstatus) or "normal"
        rtbstatus = _status_or_none(asset.rtbstatus) or "normal"
        fields = dict(
            asset_name=asset.asset_name,
            fleet_id=asset.fleet_id,
            mdstatus=mdstatus,
            mdmax=asset.mdmax,
            rtbstatus=rtbstatus,
            rtbhealth=asset.rtbhealth,
            last_operation_date=ensure_utc(asset.last_operation_date),
            polled_at=now,
        )
        current = self.db.get(HumsStatusCurrent, asset.asset_id)
        if current is None:
            current = HumsStatusCurrent(gpms_asset_id=asset.asset_id, **fields)
            self.db.add(current)
        else:
            for key, value in fields.items():
                setattr(current, key, value)

        snapshot = HumsStatusSnapshot(gpms_asset_id=asset.asset_id, **fields)
        self.db.add(snapshot)

    def list_mapped(
        self, *, customer_id: int | None = None
    ) -> list[HumsAircraftStatus]:
        """HUMS status for active mapped GPMS assets only."""
        query = select(GpmsAssetMapping).where(GpmsAssetMapping.is_active.is_(True))
        if customer_id is not None:
            query = query.where(GpmsAssetMapping.customer_id == customer_id)

        mappings = self.db.scalars(
            query.order_by(GpmsAssetMapping.brazos_tail_number)
        ).all()

        result: list[HumsAircraftStatus] = []
        for mapping in mappings:
            status = self.db.get(HumsStatusCurrent, mapping.gpms_asset_id)
            if status is None:
                result.append(
                    HumsAircraftStatus(
                        gpms_asset_id=mapping.gpms_asset_id,
                        tail_number=mapping.brazos_tail_number,
                        asset_name=mapping.gpms_asset_name,
                        mdstatus="pending",
                        rtbstatus="pending",
                        mdmax=None,
                        rtbhealth=None,
                        last_operation_date=None,
                        polled_at=None,
                        gpms_portal_url=_portal_url(mapping.gpms_asset_id),
                    )
                )
                continue
            result.append(
                HumsAircraftStatus(
                    gpms_asset_id=status.gpms_asset_id,
                    tail_number=mapping.brazos_tail_number,
                    asset_name=status.asset_name or mapping.gpms_asset_name,
                    mdstatus=status.mdstatus,
                    rtbstatus=status.rtbstatus,
                    mdmax=status.mdmax,
                    rtbhealth=status.rtbhealth,
                    last_operation_date=ensure_utc(status.last_operation_date),
                    polled_at=ensure_utc(status.polled_at),
                    gpms_portal_url=_portal_url(status.gpms_asset_id),
                )
            )
        return result

    def list_for_customer(self, customer_id: int) -> list[HumsAircraftStatus]:
        customer = self.db.get(Customer, customer_id)
        if not customer or not customer.uses_gpms:
            return []
        return self.list_mapped(customer_id=customer_id)

    def critical_events(self, customer_id: int | None = None) -> list[CriticalEvent]:
        mapped_ids = set(self.mappings.get_active_gpms_asset_ids())
        if customer_id is not None:
            customer = self.db.get(Customer, customer_id)
            if not customer or not customer.uses_gpms:
                return []
            mapped_ids = {
                m.gpms_asset_id
                for m in self.mappings.list_active_mappings()
                if m.customer_id == customer_id
            }

        if not mapped_ids:
            return []

        query = select(HumsStatusCurrent).where(
            HumsStatusCurrent.gpms_asset_id.in_(mapped_ids),
            (HumsStatusCurrent.mdstatus == "alarm")
            | (HumsStatusCurrent.rtbstatus == "alarm"),
        )
        statuses = self.db.scalars(query).all()

        mappings_by_asset = {
            m.gpms_asset_id: m for m in self.mappings.list_active_mappings()
        }

        events: list[CriticalEvent] = []
        for status in statuses:
            mapping = mappings_by_asset.get(status.gpms_asset_id)
            tail = mapping.brazos_tail_number if mapping else None
            name = status.asset_name
            if status.mdstatus == "alarm":
                events.append(
                    CriticalEvent(
                        gpms_asset_id=status.gpms_asset_id,
                        tail_number=tail,
                        asset_name=name,
                        metric="MD",
                        status=status.mdstatus,
                        last_operation_date=ensure_utc(status.last_operation_date),
                        polled_at=ensure_utc(status.polled_at),
                    )
                )
            if status.rtbstatus == "alarm":
                events.append(
                    CriticalEvent(
                        gpms_asset_id=status.gpms_asset_id,
                        tail_number=tail,
                        asset_name=name,
                        metric="RTB",
                        status=status.rtbstatus,
                        last_operation_date=ensure_utc(status.last_operation_date),
                        polled_at=ensure_utc(status.polled_at),
                    )
                )
        return events
