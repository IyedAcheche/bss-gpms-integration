"""Idempotent seed for default customer and GPMS ↔ Brazos mappings.

Runs on app startup and via scripts/seed_mappings.py.
Only seeded mappings are polled (see gpms_asset_mappings.is_active).
"""

from sqlalchemy import select

from app.db import SessionLocal, init_db
from app.models.customer import Customer
from app.models.mapping import GpmsAssetMapping

DEFAULT_CUSTOMER_NAME = "Brazos Dev"
DEFAULT_MAPPINGS = [
    {
        "gpms_asset_id": 223,
        "brazos_tail_number": "N407NW",
        "gpms_asset_name": "N407NW",
    },
]


def seed_mappings() -> None:
    init_db()
    db = SessionLocal()
    try:
        customer = db.scalar(
            select(Customer).where(Customer.name == DEFAULT_CUSTOMER_NAME)
        )
        if customer is None:
            customer = Customer(name=DEFAULT_CUSTOMER_NAME, uses_gpms=True)
            db.add(customer)
            db.flush()

        for item in DEFAULT_MAPPINGS:
            existing = db.scalar(
                select(GpmsAssetMapping).where(
                    GpmsAssetMapping.gpms_asset_id == item["gpms_asset_id"]
                )
            )
            if existing is None:
                db.add(
                    GpmsAssetMapping(
                        customer_id=customer.id,
                        gpms_asset_id=item["gpms_asset_id"],
                        brazos_tail_number=item["brazos_tail_number"],
                        gpms_asset_name=item.get("gpms_asset_name"),
                        is_active=True,
                    )
                )
            else:
                existing.brazos_tail_number = item["brazos_tail_number"]
                existing.is_active = True
                if item.get("gpms_asset_name"):
                    existing.gpms_asset_name = item["gpms_asset_name"]

        db.commit()
    finally:
        db.close()
