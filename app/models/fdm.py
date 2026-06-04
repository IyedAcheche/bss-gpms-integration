from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class FdmOperation(Base):
    __tablename__ = "fdm_operations"
    __table_args__ = (
        UniqueConstraint("gpms_asset_id", "operation_id", name="uq_asset_operation"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    gpms_asset_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    operation_id: Mapped[int] = mapped_column(Integer, nullable=False)
    start_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    flight_time: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_filename: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    raw_csv: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class FdmStateSample(Base):
    """One row per ~2s sample from exportstates CSV."""

    __tablename__ = "fdm_state_samples"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    gpms_asset_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    operation_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    row_index: Mapped[int] = mapped_column(Integer, nullable=False)

    timestamp: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    latitude: Mapped[Optional[float]] = mapped_column(Float)
    longitude: Mapped[Optional[float]] = mapped_column(Float)
    altitude: Mapped[Optional[float]] = mapped_column(Float)
    heading: Mapped[Optional[float]] = mapped_column(Float)
    ground_speed: Mapped[Optional[float]] = mapped_column(Float)
    gps_latitude: Mapped[Optional[float]] = mapped_column(Float)
    gps_longitude: Mapped[Optional[float]] = mapped_column(Float)
    gps_altitude: Mapped[Optional[float]] = mapped_column(Float)
    gps_ground_speed: Mapped[Optional[float]] = mapped_column(Float)
    pitch: Mapped[Optional[float]] = mapped_column(Float)
    roll: Mapped[Optional[float]] = mapped_column(Float)
    pitch_rate: Mapped[Optional[float]] = mapped_column(Float)
    roll_rate: Mapped[Optional[float]] = mapped_column(Float)
    yaw_rate: Mapped[Optional[float]] = mapped_column(Float)
    acceleration_x: Mapped[Optional[float]] = mapped_column(Float)
    acceleration_y: Mapped[Optional[float]] = mapped_column(Float)
    acceleration_z: Mapped[Optional[float]] = mapped_column(Float)
    normalized_acceleration: Mapped[Optional[float]] = mapped_column(Float)
    wander: Mapped[Optional[float]] = mapped_column(Float)
    ng: Mapped[Optional[float]] = mapped_column(Float)
    np: Mapped[Optional[float]] = mapped_column(Float)
    nr: Mapped[Optional[float]] = mapped_column(Float)
    torque: Mapped[Optional[float]] = mapped_column(Float)
    mgt: Mapped[Optional[float]] = mapped_column(Float)
    xot: Mapped[Optional[float]] = mapped_column(Float)
    mr_speed_roc: Mapped[Optional[float]] = mapped_column(Float)
    oat: Mapped[Optional[float]] = mapped_column(Float)
    barometric_pressure: Mapped[Optional[float]] = mapped_column(Float)
    pressure_altitude: Mapped[Optional[float]] = mapped_column(Float)
    radar_altitude: Mapped[Optional[float]] = mapped_column(Float)
    indicated_airspeed: Mapped[Optional[float]] = mapped_column(Float)
    altitude_rate: Mapped[Optional[float]] = mapped_column(Float)
    cpi: Mapped[Optional[float]] = mapped_column(Float)
    wind_speed: Mapped[Optional[float]] = mapped_column(Float)
    wind_direction: Mapped[Optional[float]] = mapped_column(Float)


class FdmIngestCursor(Base):
    """Per mapped asset: incremental FDM poll state."""

    __tablename__ = "fdm_ingest_cursors"

    gpms_asset_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    last_checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    backfill_complete: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
