from __future__ import annotations

from typing import Union

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.api.deps import db_session
from app.schemas.aircraft import CachedAircraft, FdmExportReport
from app.schemas.fdm import FdmOperationOut, FdmStateRow, FdmStateRowFull
from app.services.fdm_service import FdmService
from app.services.gpms_client import GpmsApiError
from app.services.mapping_service import MappingService

router = APIRouter(prefix="/api/fdm", tags=["fdm"])


def _require_mapped(db: Session, asset_id: int) -> None:
    if MappingService(db).get_mapping_for_asset(asset_id) is None:
        raise HTTPException(
            status_code=404,
            detail=f"GPMS asset {asset_id} is not in the active mapping table",
        )


@router.get(
    "/aircraft",
    response_model=list[CachedAircraft],
    summary="List mapped aircraft (FDM)",
)
def list_aircraft(db: Session = Depends(db_session)) -> list[CachedAircraft]:
    """Same data as `GET /api/aircraft` — mapped aircraft with HUMS + operation counts."""
    return FdmService(db).list_mapped_aircraft()


@router.get(
    "/aircraft/{asset_id}",
    response_model=CachedAircraft,
    summary="Get mapped aircraft (FDM)",
)
def get_aircraft(asset_id: int, db: Session = Depends(db_session)) -> CachedAircraft:
    """Cached HUMS fields and operation count for one mapped GPMS asset."""
    _require_mapped(db, asset_id)
    asset = FdmService(db).get_mapped_aircraft(asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset


@router.get(
    "/aircraft/{asset_id}/operations",
    response_model=list[FdmOperationOut],
    summary="List ingested flights",
)
def list_operations(
    asset_id: int,
    limit: int = 100,
    db: Session = Depends(db_session),
) -> list[FdmOperationOut]:
    """Ingested operations from Postgres, newest first."""
    _require_mapped(db, asset_id)
    return FdmService(db).list_operations(asset_id, limit=limit)


@router.post(
    "/aircraft/{asset_id}/operations/{operation_id}/ingest",
    response_model=dict,
    summary="Ingest one operation from GPMS (live)",
)
def ingest_operation(
    asset_id: int,
    operation_id: int,
    db: Session = Depends(db_session),
) -> dict:
    """Fetches exportstates CSV from GPMS and stores operation + samples. Idempotent."""
    _require_mapped(db, asset_id)
    service = FdmService(db)
    if service.operation_exists(asset_id, operation_id):
        return {"status": "already_ingested", "operation_id": operation_id}
    try:
        row = service.ingest_operation(asset_id, operation_id)
        return {
            "status": "ingested",
            "operation_id": operation_id,
            "source_filename": row.source_filename,
        }
    except GpmsApiError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get(
    "/aircraft/{asset_id}/operations/{operation_id}/exportstates",
    response_model=FdmExportReport,
    summary="Exportstates report (parsed rows)",
)
def get_exportstates(
    asset_id: int,
    operation_id: int,
    row_limit: int = 500,
    db: Session = Depends(db_session),
) -> FdmExportReport:
    """Parsed FDM samples plus CSV metadata from Postgres cache."""
    _require_mapped(db, asset_id)
    report = FdmService(db).get_exportstates_report(
        asset_id, operation_id, row_limit=row_limit
    )
    if report is None:
        raise HTTPException(status_code=404, detail="Operation not yet ingested")
    return report


@router.get(
    "/aircraft/{asset_id}/operations/{operation_id}/exportstates/raw",
    response_class=PlainTextResponse,
    summary="Raw exportstates CSV",
)
def get_exportstates_raw(
    asset_id: int,
    operation_id: int,
    db: Session = Depends(db_session),
) -> str:
    """Full CSV text as stored in `fdm_operations.raw_csv`."""
    _require_mapped(db, asset_id)
    raw = FdmService(db).get_exportstates_raw(asset_id, operation_id)
    if raw is None:
        raise HTTPException(status_code=404, detail="Operation not yet ingested")
    return raw


@router.get(
    "/aircraft/{asset_id}/operations/{operation_id}/states",
    response_model=list[Union[FdmStateRow, FdmStateRowFull]],
    summary="FDM state rows (paginated)",
)
def get_states(
    asset_id: int,
    operation_id: int,
    offset: int = 0,
    limit: int = 500,
    full: bool = False,
    db: Session = Depends(db_session),
) -> list[FdmStateRow] | list[FdmStateRowFull]:
    """Paginated samples from `fdm_state_samples`. Set `full=true` for all 36 columns."""
    _require_mapped(db, asset_id)
    if not FdmService(db).operation_exists(asset_id, operation_id):
        raise HTTPException(status_code=404, detail="Operation not ingested")
    return FdmService(db).get_state_rows(
        asset_id, operation_id, offset=offset, limit=limit, full=full
    )
