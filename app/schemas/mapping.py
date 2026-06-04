from typing import Optional

from pydantic import BaseModel, Field


class AssetMappingCreate(BaseModel):
    customer_id: int
    gpms_asset_id: int
    gpms_fleet_id: Optional[int] = None
    brazos_tail_number: str = Field(..., min_length=1, max_length=32)
    gpms_asset_name: Optional[str] = None
    is_active: bool = True


class AssetMappingOut(BaseModel):
    id: int
    customer_id: int
    gpms_asset_id: int
    gpms_fleet_id: Optional[int]
    brazos_tail_number: str
    gpms_asset_name: Optional[str]
    is_active: bool

    model_config = {"from_attributes": True}
