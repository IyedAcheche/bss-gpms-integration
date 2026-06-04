from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.fdm import FdmIngestCursor, FdmOperation, FdmStateSample
from app.models.hums import HumsStatusCurrent
from app.schemas.aircraft import CachedAircraft, FdmExportReport
from app.schemas.fdm import FdmOperationOut, FdmStateRow, FdmStateRowFull
from app.services.csv_ingest import HEADER_MAP, build_states_filename, parse_states_csv
from app.services.gpms_client import GpmsApiError, GpmsClient
from app.services.gpms_types import GpmsOperation
from app.services.mapping_service import MappingService
from app.services.token_manager import TokenManager
from app.time_utils import ensure_utc, utc_now

logger = logging.getLogger(__name__)


class FdmService:
    def __init__(self, db: Session):
        self.db = db
        self.mappings = MappingService(db)

    # ------------------------------------------------------------------
    # Read methods — DB only, mapped assets only
    # ------------------------------------------------------------------

    def list_mapped_aircraft(self) -> list[CachedAircraft]:
        result: list[CachedAircraft] = []
        for mapping in self.mappings.list_active_mappings():
            hums = self.db.get(HumsStatusCurrent, mapping.gpms_asset_id)
            op_count = self.db.scalar(
                select(func.count(FdmOperation.id)).where(
                    FdmOperation.gpms_asset_id == mapping.gpms_asset_id
                )
            ) or 0
            if hums is None:
                result.append(
                    CachedAircraft(
                        asset_id=mapping.gpms_asset_id,
                        brazos_tail_number=mapping.brazos_tail_number,
                        asset_name=mapping.gpms_asset_name,
                        operation_count=op_count,
                        hums_cached=False,
                    )
                )
            else:
                result.append(
                    CachedAircraft(
                        asset_id=hums.gpms_asset_id,
                        brazos_tail_number=mapping.brazos_tail_number,
                        fleet_id=hums.fleet_id,
                        asset_name=hums.asset_name or mapping.gpms_asset_name,
                        mdstatus=hums.mdstatus,
                        mdmax=hums.mdmax,
                        rtbstatus=hums.rtbstatus,
                        rtbhealth=hums.rtbhealth,
                        last_operation_date=hums.last_operation_date,
                        polled_at=hums.polled_at,
                        operation_count=op_count,
                        hums_cached=True,
                    )
                )
        return result

    def get_mapped_aircraft(self, asset_id: int) -> CachedAircraft | None:
        mapping = self.mappings.get_mapping_for_asset(asset_id)
        if mapping is None:
            return None
        items = self.list_mapped_aircraft()
        return next((a for a in items if a.asset_id == asset_id), None)

    def list_operations(self, asset_id: int, *, limit: int = 100) -> list[FdmOperationOut]:
        if self.mappings.get_mapping_for_asset(asset_id) is None:
            return []
        rows = self.db.scalars(
            select(FdmOperation)
            .where(FdmOperation.gpms_asset_id == asset_id)
            .order_by(FdmOperation.start_time.desc())
            .limit(limit)
        ).all()
        return [
            FdmOperationOut(
                operation_id=r.operation_id,
                gpms_asset_id=r.gpms_asset_id,
                start_time=r.start_time,
                end_time=r.end_time,
                flight_time=r.flight_time,
                ingested_at=r.ingested_at,
                is_ingested=True,
            )
            for r in rows
        ]

    def operation_exists(self, asset_id: int, operation_id: int) -> bool:
        return (
            self.db.scalar(
                select(FdmOperation.id).where(
                    FdmOperation.gpms_asset_id == asset_id,
                    FdmOperation.operation_id == operation_id,
                )
            )
            is not None
        )

    def get_state_rows(
        self,
        asset_id: int,
        operation_id: int,
        *,
        offset: int = 0,
        limit: int = 500,
        full: bool = False,
    ) -> list[FdmStateRow] | list[FdmStateRowFull]:
        rows = self.db.scalars(
            select(FdmStateSample)
            .where(
                FdmStateSample.gpms_asset_id == asset_id,
                FdmStateSample.operation_id == operation_id,
            )
            .order_by(FdmStateSample.row_index)
            .offset(offset)
            .limit(limit)
        ).all()
        schema = FdmStateRowFull if full else FdmStateRow
        return [schema.model_validate(r) for r in rows]

    def get_exportstates_report(
        self,
        asset_id: int,
        operation_id: int,
        *,
        row_limit: int = 500,
    ) -> FdmExportReport | None:
        op_row = self.db.scalar(
            select(FdmOperation).where(
                FdmOperation.gpms_asset_id == asset_id,
                FdmOperation.operation_id == operation_id,
            )
        )
        if op_row is None:
            return None

        sample_count = self.db.scalar(
            select(func.count(FdmStateSample.id)).where(
                FdmStateSample.gpms_asset_id == asset_id,
                FdmStateSample.operation_id == operation_id,
            )
        ) or 0

        state_rows = self.get_state_rows(asset_id, operation_id, limit=row_limit, full=True)
        row_dicts = [r.model_dump() for r in state_rows]

        raw_csv = op_row.raw_csv or ""
        lines = raw_csv.splitlines()

        return FdmExportReport(
            gpms_asset_id=asset_id,
            operation_id=operation_id,
            csv_line_count=len(lines) if lines else sample_count + 1,
            csv_byte_count=len(raw_csv.encode("utf-8")),
            csv_header=lines[0] if lines else ",".join(k.title() for k in HEADER_MAP),
            raw_csv_preview="\n".join(lines[:6]),
            rows=row_dicts,
        )

    def get_exportstates_raw(self, asset_id: int, operation_id: int) -> str | None:
        op_row = self.db.scalar(
            select(FdmOperation).where(
                FdmOperation.gpms_asset_id == asset_id,
                FdmOperation.operation_id == operation_id,
            )
        )
        if op_row is None:
            return None
        return op_row.raw_csv or ""

    # ------------------------------------------------------------------
    # Write methods — background job + manual ingest
    # ------------------------------------------------------------------

    def ingest_operation(
        self,
        asset_id: int,
        operation_id: int,
        *,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        flight_time: float | None = None,
    ) -> FdmOperation:
        self.mappings.require_mapped_asset(asset_id)

        if self.operation_exists(asset_id, operation_id):
            row = self.db.scalar(
                select(FdmOperation).where(
                    FdmOperation.gpms_asset_id == asset_id,
                    FdmOperation.operation_id == operation_id,
                )
            )
            if row is None:
                raise RuntimeError(
                    f"operation_exists=True but row missing: asset={asset_id} op={operation_id}"
                )
            return row

        if start_time is None:
            token = TokenManager(self.db).get_valid_token()
            with GpmsClient(get_settings(), token) as client:
                op = client.get_operation(asset_id, operation_id)
                if op:
                    start_time = op.start_time
                    end_time = op.end_time
                    flight_time = op.flight_time

        token = TokenManager(self.db).get_valid_token()
        with GpmsClient(get_settings(), token) as client:
            csv_bytes = client.export_states_csv(asset_id, operation_id)

        raw_csv = csv_bytes.decode("utf-8-sig", errors="replace")
        mapping = self.mappings.get_mapping_for_asset(asset_id)
        tail = mapping.brazos_tail_number if mapping else f"ASSET{asset_id}"
        filename = build_states_filename(tail, start_time)

        operation = FdmOperation(
            gpms_asset_id=asset_id,
            operation_id=operation_id,
            start_time=ensure_utc(start_time),
            end_time=ensure_utc(end_time),
            flight_time=flight_time,
            ingested_at=utc_now(),
            source_filename=filename,
            raw_csv=raw_csv,
        )
        self.db.add(operation)
        self.db.flush()

        samples = parse_states_csv(
            csv_bytes, gpms_asset_id=asset_id, operation_id=operation_id
        )
        self.db.add_all(samples)
        self.db.commit()
        self.db.refresh(operation)
        return operation

    def poll_new_imports(self) -> int:
        mapped_ids = self.mappings.get_active_gpms_asset_ids()
        if not mapped_ids:
            logger.warning("FDM poll skipped: no active mappings")
            return 0

        token = TokenManager(self.db).get_valid_token()
        ingested_count = 0
        settings = get_settings()

        with GpmsClient(settings, token) as client:
            for gpms_asset_id in mapped_ids:
                try:
                    ingested_count += self._poll_asset_imports(
                        client, gpms_asset_id, settings.fdm_operations_fetch_limit
                    )
                except Exception:
                    logger.exception(
                        "FDM poll failed for mapped asset %s", gpms_asset_id
                    )
                    self.db.rollback()

        return ingested_count

    def _poll_asset_imports(
        self, client: GpmsClient, gpms_asset_id: int, operations_limit: int
    ) -> int:
        now = utc_now()
        cursor = self.db.get(FdmIngestCursor, gpms_asset_id)
        operation_ids: list[int] = []
        ops_by_id: dict[int, GpmsOperation] = {}
        backfill_complete = False

        if cursor is None or not cursor.backfill_complete:
            try:
                operations = client.get_operations(gpms_asset_id, limit=operations_limit)
            except GpmsApiError:
                logger.exception(
                    "Failed to list operations for mapped asset %s", gpms_asset_id
                )
                return 0
            ops_by_id = {op.operation_id: op for op in operations}
            operation_ids = list(ops_by_id.keys())
            backfill_complete = len(operations) < operations_limit
        else:
            start = ensure_utc(cursor.last_checked_at) or now
            start_str = start.strftime("%Y-%m-%dT%H:%M:%SZ")
            try:
                operation_ids = client.get_new_imports(gpms_asset_id, start_str)
            except GpmsApiError:
                logger.exception(
                    "newimports failed for mapped asset %s", gpms_asset_id
                )
                return 0
            backfill_complete = True

        ingested = 0
        for operation_id in operation_ids:
            if self.operation_exists(gpms_asset_id, operation_id):
                continue
            op_meta = ops_by_id.get(operation_id)
            try:
                self.ingest_operation(
                    gpms_asset_id,
                    operation_id,
                    start_time=op_meta.start_time if op_meta else None,
                    end_time=op_meta.end_time if op_meta else None,
                    flight_time=op_meta.flight_time if op_meta else None,
                )
                ingested += 1
            except GpmsApiError:
                logger.exception(
                    "Ingest failed asset=%s operation=%s",
                    gpms_asset_id,
                    operation_id,
                )
                self.db.rollback()

        if cursor is None:
            cursor = FdmIngestCursor(
                gpms_asset_id=gpms_asset_id,
                last_checked_at=now,
                backfill_complete=backfill_complete,
            )
            self.db.add(cursor)
        else:
            cursor.last_checked_at = now
            if backfill_complete:
                cursor.backfill_complete = True

        self.db.commit()
        return ingested
