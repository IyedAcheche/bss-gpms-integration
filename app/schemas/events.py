from typing import Optional

from pydantic import BaseModel

from app.time_utils import OptionalUtcDatetime, UtcDatetime


class CriticalEvent(BaseModel):
    gpms_asset_id: int
    tail_number: Optional[str]
    asset_name: Optional[str]
    metric: str
    status: str
    last_operation_date: OptionalUtcDatetime = None
    polled_at: UtcDatetime
