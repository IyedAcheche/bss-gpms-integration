from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.customer import Customer


class GpmsAssetMapping(Base):
    """Maps a GPMS asset_id to a Brazos tail number.

    Only rows with is_active=True are polled (HUMS + FDM jobs) and returned by read APIs.
    """

    __tablename__ = "gpms_asset_mappings"
    __table_args__ = (UniqueConstraint("gpms_asset_id", name="uq_gpms_asset_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=False)
    gpms_asset_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    gpms_fleet_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    brazos_tail_number: Mapped[str] = mapped_column(String(32), nullable=False)
    gpms_asset_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    customer: Mapped["Customer"] = relationship(back_populates="asset_mappings")
