from datetime import datetime, timezone

from app.time_utils import ensure_utc, format_utc_iso, parse_datetime, utc_now


def test_utc_now_is_aware():
    now = utc_now()
    assert now.tzinfo is not None
    assert now.tzinfo.utcoffset(now).total_seconds() == 0


def test_ensure_utc_naive_and_offset():
    naive = datetime(2026, 6, 4, 12, 0, 0)
    assert ensure_utc(naive).tzinfo == timezone.utc
    eastern = datetime(2026, 6, 4, 8, 0, 0, tzinfo=timezone.utc)
    assert ensure_utc(eastern).hour == 8


def test_parse_datetime_z_suffix():
    dt = parse_datetime("2026-06-04T18:33:22Z")
    assert dt is not None
    assert dt.tzinfo == timezone.utc
    assert dt.hour == 18


def test_format_utc_iso():
    dt = datetime(2026, 6, 4, 18, 33, 22, tzinfo=timezone.utc)
    assert format_utc_iso(dt) == "2026-06-04T18:33:22Z"


def test_hums_status_json_uses_z_suffix():
    from app.schemas.hums import HumsAircraftStatus

    row = HumsAircraftStatus(
        gpms_asset_id=223,
        tail_number="N407NW",
        asset_name="N407NW",
        mdstatus="normal",
        rtbstatus="warning",
        mdmax=0.5,
        rtbhealth=0.75,
        last_operation_date=datetime(2026, 6, 4, 18, 33, 22, tzinfo=timezone.utc),
        polled_at=datetime(2026, 6, 4, 19, 0, 0, tzinfo=timezone.utc),
    )
    payload = row.model_dump(mode="json")
    assert payload["polled_at"].endswith("Z")
    assert payload["last_operation_date"].endswith("Z")


def test_gpms_asset_parses_utc_last_operation():
    from app.services.gpms_types import GpmsAsset

    asset = GpmsAsset.model_validate(
        {
            "asset_id": 223,
            "last_operation_date": "2026-06-04T18:33:22Z",
        }
    )
    assert asset.last_operation_date is not None
    assert asset.last_operation_date.tzinfo == timezone.utc
