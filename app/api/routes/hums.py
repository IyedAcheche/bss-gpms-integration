from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import db_session
from app.models.customer import Customer
from app.schemas.hums import HumsAircraftStatus
from app.services.hums_service import HumsService

gpms_router = APIRouter(prefix="/api", tags=["hums"])
customer_router = APIRouter(prefix="/api/customers", tags=["hums-customer"])


@gpms_router.get(
    "/hums",
    response_model=list[HumsAircraftStatus],
    summary="HUMS status (mapped aircraft)",
)
def get_gpms_hums(db: Session = Depends(db_session)) -> list[HumsAircraftStatus]:
    """Latest MD/RTB health from Postgres for all active mappings."""
    return HumsService(db).list_mapped()


@customer_router.get(
    "/{customer_id}/hums",
    response_model=list[HumsAircraftStatus],
    summary="HUMS status for one customer",
)
def get_customer_hums(
    customer_id: int, db: Session = Depends(db_session)
) -> list[HumsAircraftStatus]:
    customer = db.get(Customer, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    if not customer.uses_gpms:
        raise HTTPException(status_code=404, detail="GPMS not enabled for customer")
    return HumsService(db).list_for_customer(customer_id)
