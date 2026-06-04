from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.mapping import GpmsAssetMapping


class MappingService:
    def __init__(self, db: Session):
        self.db = db

    def list_active_mappings(self) -> list[GpmsAssetMapping]:
        return list(
            self.db.scalars(
                select(GpmsAssetMapping)
                .where(GpmsAssetMapping.is_active.is_(True))
                .order_by(GpmsAssetMapping.brazos_tail_number)
            ).all()
        )

    def get_active_gpms_asset_ids(self) -> list[int]:
        return [m.gpms_asset_id for m in self.list_active_mappings()]

    def get_mapping_for_asset(self, gpms_asset_id: int) -> GpmsAssetMapping | None:
        return self.db.scalar(
            select(GpmsAssetMapping).where(
                GpmsAssetMapping.gpms_asset_id == gpms_asset_id,
                GpmsAssetMapping.is_active.is_(True),
            )
        )

    def require_mapped_asset(self, gpms_asset_id: int) -> GpmsAssetMapping:
        mapping = self.get_mapping_for_asset(gpms_asset_id)
        if mapping is None:
            raise KeyError(f"GPMS asset {gpms_asset_id} is not in the active mapping table")
        return mapping
