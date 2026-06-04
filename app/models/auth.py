from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class GpmsAuthToken(Base):
    """Singleton row storing the current GPMS JWT."""

    __tablename__ = "gpms_auth_tokens"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    token: Mapped[str] = mapped_column(String(4096), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
