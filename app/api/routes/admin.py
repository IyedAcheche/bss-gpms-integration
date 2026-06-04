from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import db_session
from app.models.customer import Customer
from app.models.mapping import GpmsAssetMapping
from app.schemas.mapping import AssetMappingCreate, AssetMappingOut

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post("/customers", response_model=dict, summary="Create customer")
def create_customer(
    name: str, uses_gpms: bool = False, db: Session = Depends(db_session)
) -> dict:
    """Query params: `name`, `uses_gpms`."""
    customer = Customer(name=name, uses_gpms=uses_gpms)
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return {"id": customer.id, "name": customer.name, "uses_gpms": customer.uses_gpms}


@router.patch(
    "/customers/{customer_id}/gpms",
    response_model=dict,
    summary="Enable/disable GPMS for customer",
)
def set_gpms_enabled(
    customer_id: int, enabled: bool, db: Session = Depends(db_session)
) -> dict:
    customer = db.get(Customer, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    customer.uses_gpms = enabled
    db.commit()
    return {"id": customer.id, "uses_gpms": customer.uses_gpms}


@router.get(
    "/mappings",
    response_model=list[AssetMappingOut],
    summary="List all mappings (incl. inactive)",
)
def list_all_mappings(db: Session = Depends(db_session)) -> list[AssetMappingOut]:
    rows = db.scalars(select(GpmsAssetMapping).order_by(GpmsAssetMapping.brazos_tail_number)).all()
    return [AssetMappingOut.model_validate(r) for r in rows]


@router.get(
    "/customers/{customer_id}/mappings",
    response_model=list[AssetMappingOut],
    summary="Mappings for one customer",
)
def list_mappings(customer_id: int, db: Session = Depends(db_session)) -> list[AssetMappingOut]:
    rows = db.scalars(
        select(GpmsAssetMapping).where(GpmsAssetMapping.customer_id == customer_id)
    ).all()
    return [AssetMappingOut.model_validate(r) for r in rows]


@router.post("/mappings", response_model=AssetMappingOut, summary="Create mapping")
def create_mapping(
    payload: AssetMappingCreate, db: Session = Depends(db_session)
) -> AssetMappingOut:
    customer = db.get(Customer, payload.customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    existing = db.scalar(
        select(GpmsAssetMapping).where(
            GpmsAssetMapping.gpms_asset_id == payload.gpms_asset_id
        )
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Mapping already exists for GPMS asset {payload.gpms_asset_id}",
        )
    row = GpmsAssetMapping(
        customer_id=payload.customer_id,
        gpms_asset_id=payload.gpms_asset_id,
        gpms_fleet_id=payload.gpms_fleet_id,
        brazos_tail_number=payload.brazos_tail_number,
        gpms_asset_name=payload.gpms_asset_name,
        is_active=payload.is_active,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return AssetMappingOut.model_validate(row)
