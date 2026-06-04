from app.models.customer import Customer
from app.models.mapping import GpmsAssetMapping
from app.services.mapping_service import MappingService


def test_active_mappings_only(db):
    customer = Customer(name="Test", uses_gpms=True)
    db.add(customer)
    db.flush()

    db.add(
        GpmsAssetMapping(
            customer_id=customer.id,
            gpms_asset_id=91001,
            brazos_tail_number="TEST-ACTIVE",
            is_active=True,
        )
    )
    db.add(
        GpmsAssetMapping(
            customer_id=customer.id,
            gpms_asset_id=91002,
            brazos_tail_number="TEST-INACTIVE",
            is_active=False,
        )
    )
    db.flush()

    ids = MappingService(db).get_active_gpms_asset_ids()
    assert 91001 in ids
    assert 91002 not in ids
