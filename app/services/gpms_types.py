from typing import List, Optional

from pydantic import BaseModel, Field

from app.time_utils import OptionalUtcDatetime


class GpmsAsset(BaseModel):
    asset_id: int
    fleet_id: Optional[int] = None
    asset_name: Optional[str] = None
    mdstatus: str = "normal"
    mdmax: Optional[float] = None
    rtbstatus: str = "normal"
    rtbhealth: Optional[float] = None
    last_operation_date: OptionalUtcDatetime = None

    model_config = {"populate_by_name": True, "extra": "ignore"}


class GpmsFleet(BaseModel):
    fleet_id: int
    fleet_name: Optional[str] = None
    assets: List[GpmsAsset] = Field(default_factory=list)

    model_config = {"extra": "ignore"}


class GpmsOperation(BaseModel):
    operation_id: int
    start_time: OptionalUtcDatetime = None
    end_time: OptionalUtcDatetime = None
    flight_time: Optional[float] = None

    model_config = {"extra": "ignore"}
