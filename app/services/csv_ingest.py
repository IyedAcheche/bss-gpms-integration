from __future__ import annotations

import csv
import io
import re
from datetime import datetime
from typing import Any

from app.models.fdm import FdmStateSample
from app.time_utils import ensure_utc, parse_datetime

# GPMS exportstates CSV headers (normalized to snake_case DB columns)
HEADER_MAP: dict[str, str] = {
    "timestamp": "timestamp",
    "latitude": "latitude",
    "longitude": "longitude",
    "altitude": "altitude",
    "heading": "heading",
    "ground speed": "ground_speed",
    "gps latitude": "gps_latitude",
    "gps longitude": "gps_longitude",
    "gps altitude": "gps_altitude",
    "gps ground speed": "gps_ground_speed",
    "pitch": "pitch",
    "roll": "roll",
    "pitch rate": "pitch_rate",
    "roll rate": "roll_rate",
    "yaw rate": "yaw_rate",
    "acceleration x": "acceleration_x",
    "acceleration y": "acceleration_y",
    "acceleration z": "acceleration_z",
    "normalized acceleration": "normalized_acceleration",
    "wander": "wander",
    "ng": "ng",
    "np": "np",
    "nr": "nr",
    "torque": "torque",
    "mgt": "mgt",
    "xot": "xot",
    "mr speed roc": "mr_speed_roc",
    "oat": "oat",
    "barometric pressure": "barometric_pressure",
    "pressure altitude": "pressure_altitude",
    "radar altitude": "radar_altitude",
    "indicated airspeed": "indicated_airspeed",
    "altitude rate": "altitude_rate",
    "cpi": "cpi",
    "wind speed": "wind_speed",
    "wind direction": "wind_direction",
}


def _normalize_header(header: str) -> str:
    key = header.strip().lower()
    return HEADER_MAP.get(key, re.sub(r"[^a-z0-9]+", "_", key).strip("_"))


def _parse_float(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _parse_timestamp(value: str | None) -> datetime | None:
    return parse_datetime(value)


def parse_states_csv(
    content: bytes,
    *,
    gpms_asset_id: int,
    operation_id: int,
) -> list[FdmStateSample]:
    text = content.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        return []

    column_map = {_normalize_header(h): h for h in reader.fieldnames if h}

    samples: list[FdmStateSample] = []
    for row_index, row in enumerate(reader):
        values: dict[str, Any] = {
            "gpms_asset_id": gpms_asset_id,
            "operation_id": operation_id,
            "row_index": row_index,
        }
        for field, header in column_map.items():
            raw = row.get(header)
            if field == "timestamp":
                values[field] = _parse_timestamp(raw)
            else:
                values[field] = _parse_float(raw)
        samples.append(FdmStateSample(**values))
    return samples


def build_states_filename(
    tail_number: str,
    start_time: datetime | None,
) -> str:
    tail = tail_number or "UNKNOWN"
    if start_time:
        utc = ensure_utc(start_time)
        assert utc is not None
        return f"{tail}_{utc.strftime('%Y-%m-%d_%H%M%S')}_STATES.csv"
    return f"{tail}_UNKNOWN_STATES.csv"
