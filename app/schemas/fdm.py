from typing import Optional

from pydantic import BaseModel

from app.time_utils import OptionalUtcDatetime


class FdmOperationOut(BaseModel):
    operation_id: int
    gpms_asset_id: int
    start_time: OptionalUtcDatetime = None
    end_time: OptionalUtcDatetime = None
    flight_time: Optional[float]
    ingested_at: OptionalUtcDatetime = None
    is_ingested: bool

    model_config = {"from_attributes": True}


class FdmStateRow(BaseModel):
    """Subset of columns for lightweight API responses."""

    row_index: int
    timestamp: OptionalUtcDatetime = None
    latitude: Optional[float]
    longitude: Optional[float]
    altitude: Optional[float]
    heading: Optional[float]
    ground_speed: Optional[float]
    pitch: Optional[float]
    roll: Optional[float]
    indicated_airspeed: Optional[float]

    model_config = {"from_attributes": True}


class FdmStateRowFull(BaseModel):
    """All ingested GPMS exportstates columns."""

    row_index: int
    timestamp: OptionalUtcDatetime = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    altitude: Optional[float] = None
    heading: Optional[float] = None
    ground_speed: Optional[float] = None
    gps_latitude: Optional[float] = None
    gps_longitude: Optional[float] = None
    gps_altitude: Optional[float] = None
    gps_ground_speed: Optional[float] = None
    pitch: Optional[float] = None
    roll: Optional[float] = None
    pitch_rate: Optional[float] = None
    roll_rate: Optional[float] = None
    yaw_rate: Optional[float] = None
    acceleration_x: Optional[float] = None
    acceleration_y: Optional[float] = None
    acceleration_z: Optional[float] = None
    normalized_acceleration: Optional[float] = None
    wander: Optional[float] = None
    ng: Optional[float] = None
    np: Optional[float] = None
    nr: Optional[float] = None
    torque: Optional[float] = None
    mgt: Optional[float] = None
    xot: Optional[float] = None
    mr_speed_roc: Optional[float] = None
    oat: Optional[float] = None
    barometric_pressure: Optional[float] = None
    pressure_altitude: Optional[float] = None
    radar_altitude: Optional[float] = None
    indicated_airspeed: Optional[float] = None
    altitude_rate: Optional[float] = None
    cpi: Optional[float] = None
    wind_speed: Optional[float] = None
    wind_direction: Optional[float] = None

    model_config = {"from_attributes": True}
