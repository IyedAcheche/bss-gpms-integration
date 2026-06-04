from datetime import datetime
from typing import Literal, Optional

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base

HealthStatus = Literal["normal", "warning", "alarm"]


class HumsStatusCurrent(Base):
    """Latest polled health status per GPMS asset."""

    __tablename__ = "hums_status_current"

    gpms_asset_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    asset_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    fleet_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    mdstatus: Mapped[str] = mapped_column(String(16), nullable=False)
    mdmax: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    rtbstatus: Mapped[str] = mapped_column(String(16), nullable=False)
    rtbhealth: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    last_operation_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    polled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class HumsStatusSnapshot(Base):
    """Historical HUMS status for reporting."""

    __tablename__ = "hums_status_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    gpms_asset_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    asset_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    fleet_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    mdstatus: Mapped[str] = mapped_column(String(16), nullable=False)
    mdmax: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    rtbstatus: Mapped[str] = mapped_column(String(16), nullable=False)
    rtbhealth: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    last_operation_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    polled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
