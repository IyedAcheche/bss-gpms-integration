from typing import Any, Optional

from pydantic import BaseModel

from app.time_utils import OptionalUtcDatetime


class CachedAircraft(BaseModel):
    """HUMS health fields for one mapped GPMS asset (from DB cache)."""

    asset_id: int
    brazos_tail_number: str
    fleet_id: Optional[int] = None
    asset_name: Optional[str] = None
    mdstatus: Optional[str] = None
    mdmax: Optional[float] = None
    rtbstatus: Optional[str] = None
    rtbhealth: Optional[float] = None
    last_operation_date: OptionalUtcDatetime = None
    polled_at: OptionalUtcDatetime = None
    operation_count: int = 0
    hums_cached: bool = False


class FdmExportReport(BaseModel):
    gpms_asset_id: int
    operation_id: int
    csv_line_count: int
    csv_byte_count: int
    csv_header: str
    raw_csv_preview: str
    rows: list[dict[str, Any]]
