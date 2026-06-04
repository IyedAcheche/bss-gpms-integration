from typing import Optional

from pydantic import BaseModel

from app.time_utils import OptionalUtcDatetime, UtcDatetime


class HumsAircraftStatus(BaseModel):
    gpms_asset_id: int
    tail_number: Optional[str]
    asset_name: Optional[str]
    mdstatus: str
    rtbstatus: str
    mdmax: Optional[float]
    rtbhealth: Optional[float]
    last_operation_date: OptionalUtcDatetime = None
    polled_at: OptionalUtcDatetime = None
    gpms_portal_url: Optional[str] = None

    model_config = {"from_attributes": True}
