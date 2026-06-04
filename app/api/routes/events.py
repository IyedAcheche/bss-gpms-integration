from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import db_session
from app.schemas.events import CriticalEvent
from app.services.hums_service import HumsService

router = APIRouter(prefix="/api")


@router.get(
    "/customers/{customer_id}/events/critical",
    response_model=list[CriticalEvent],
    tags=["events-customer"],
    summary="Critical events for one customer",
)
def critical_events_for_customer(
    customer_id: int, db: Session = Depends(db_session)
) -> list[CriticalEvent]:
    """MD/RTB alarms for mapped aircraft belonging to the customer."""
    return HumsService(db).critical_events(customer_id=customer_id)


@router.get(
    "/events/critical",
    response_model=list[CriticalEvent],
    tags=["events"],
    summary="Critical events (all mapped)",
)
def critical_events_all(db: Session = Depends(db_session)) -> list[CriticalEvent]:
    """MD/RTB status `alarm` only (warnings excluded) for mapped aircraft."""
    return HumsService(db).critical_events()
