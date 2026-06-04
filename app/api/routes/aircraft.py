from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import db_session
from app.schemas.aircraft import CachedAircraft
from app.schemas.mapping import AssetMappingOut
from app.services.fdm_service import FdmService
from app.services.mapping_service import MappingService

router = APIRouter(prefix="/api")


@router.get(
    "/mappings",
    response_model=list[AssetMappingOut],
    tags=["mappings"],
    summary="List active mappings",
)
def list_mappings(db: Session = Depends(db_session)) -> list[AssetMappingOut]:
    """All active GPMS ↔ Brazos mappings (scope for polls and UI)."""
    rows = MappingService(db).list_active_mappings()
    return [AssetMappingOut.model_validate(r) for r in rows]


@router.get(
    "/aircraft",
    response_model=list[CachedAircraft],
    tags=["aircraft"],
    summary="List mapped aircraft",
)
def list_aircraft(db: Session = Depends(db_session)) -> list[CachedAircraft]:
    """Mapped aircraft with cached HUMS + ingested operation counts."""
    return FdmService(db).list_mapped_aircraft()


@router.get(
    "/aircraft/{asset_id}",
    response_model=CachedAircraft,
    tags=["aircraft"],
    summary="Get one mapped aircraft",
)
def get_aircraft(asset_id: int, db: Session = Depends(db_session)) -> CachedAircraft:
    asset = FdmService(db).get_mapped_aircraft(asset_id)
    if asset is None:
        raise HTTPException(
            status_code=404,
            detail="Asset not in mapping table or HUMS poll has not run yet",
        )
    return asset
