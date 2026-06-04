from datetime import timezone

from app.services.csv_ingest import build_states_filename, parse_states_csv

SAMPLE_CSV = """Timestamp,Latitude,Longitude,Altitude,Heading,Ground Speed,Gps Latitude,Gps Longitude,Gps Altitude,Gps Ground Speed,Pitch,Roll,Pitch Rate,Roll Rate,Yaw Rate,Acceleration X,Acceleration Y,Acceleration Z,Normalized Acceleration,Wander,NG,NP,NR,Torque,MGT,XOT,MR Speed Roc,OAT,Barometric Pressure,Pressure Altitude,Radar Altitude,Indicated Airspeed,Altitude Rate,CPI,Wind Speed,Wind Direction
2026-06-04T13:27:35Z,29.76,-95.37,1200,180,45,29.76,-95.37,1200,45,1.2,-0.5,0.01,-0.02,0.03,0.1,0.2,1.0,1.01,0.0,100,200,300,50,700,400,1.0,15,29.92,1200,1180,90,-100,0.5,10,270
"""


def test_parse_states_csv_row_count():
    samples = parse_states_csv(
        SAMPLE_CSV.encode("utf-8"), gpms_asset_id=20, operation_id=999
    )
    assert len(samples) == 1
    assert samples[0].latitude == 29.76
    assert samples[0].operation_id == 999
    assert samples[0].timestamp.tzinfo is not None


def test_build_states_filename():
    from datetime import datetime

    dt = datetime(2026, 6, 4, 13, 27, 35, tzinfo=timezone.utc)
    name = build_states_filename("N407NW", dt)
    assert name == "N407NW_2026-06-04_132735_STATES.csv"
