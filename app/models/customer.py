from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.mapping import GpmsAssetMapping


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    uses_gpms: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    asset_mappings: Mapped[list["GpmsAssetMapping"]] = relationship(
        back_populates="customer"
    )
