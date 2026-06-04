"""Initial schema for mapping-scoped GPMS cache.

Tables: customers, gpms_asset_mappings, gpms_auth_tokens, hums_status_*,
fdm_operations, fdm_state_samples, fdm_ingest_cursors.

Revision ID: 001
Revises:
Create Date: 2026-06-04

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "customers",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("uses_gpms", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "gpms_auth_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("token", sa.String(length=4096), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "gpms_asset_mappings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("gpms_asset_id", sa.Integer(), nullable=False),
        sa.Column("gpms_fleet_id", sa.Integer(), nullable=True),
        sa.Column("brazos_tail_number", sa.String(length=32), nullable=False),
        sa.Column("gpms_asset_name", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("gpms_asset_id", name="uq_gpms_asset_id"),
    )
    op.create_index("ix_gpms_asset_mappings_gpms_asset_id", "gpms_asset_mappings", ["gpms_asset_id"])

    op.create_table(
        "hums_status_current",
        sa.Column("gpms_asset_id", sa.Integer(), nullable=False),
        sa.Column("asset_name", sa.String(length=255), nullable=True),
        sa.Column("fleet_id", sa.Integer(), nullable=True),
        sa.Column("mdstatus", sa.String(length=16), nullable=False),
        sa.Column("mdmax", sa.Float(), nullable=True),
        sa.Column("rtbstatus", sa.String(length=16), nullable=False),
        sa.Column("rtbhealth", sa.Float(), nullable=True),
        sa.Column("last_operation_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("polled_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("gpms_asset_id"),
    )
    op.create_table(
        "hums_status_snapshots",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("gpms_asset_id", sa.Integer(), nullable=False),
        sa.Column("asset_name", sa.String(length=255), nullable=True),
        sa.Column("fleet_id", sa.Integer(), nullable=True),
        sa.Column("mdstatus", sa.String(length=16), nullable=False),
        sa.Column("mdmax", sa.Float(), nullable=True),
        sa.Column("rtbstatus", sa.String(length=16), nullable=False),
        sa.Column("rtbhealth", sa.Float(), nullable=True),
        sa.Column("last_operation_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("polled_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_hums_status_snapshots_gpms_asset_id", "hums_status_snapshots", ["gpms_asset_id"])

    op.create_table(
        "fdm_operations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("gpms_asset_id", sa.Integer(), nullable=False),
        sa.Column("operation_id", sa.Integer(), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("flight_time", sa.Float(), nullable=True),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_filename", sa.String(length=512), nullable=True),
        sa.Column("raw_csv", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("gpms_asset_id", "operation_id", name="uq_asset_operation"),
    )
    op.create_index("ix_fdm_operations_gpms_asset_id", "fdm_operations", ["gpms_asset_id"])

    op.create_table(
        "fdm_ingest_cursors",
        sa.Column("gpms_asset_id", sa.Integer(), nullable=False),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("backfill_complete", sa.Boolean(), nullable=False, server_default="false"),
        sa.PrimaryKeyConstraint("gpms_asset_id"),
    )

    op.create_table(
        "fdm_state_samples",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("gpms_asset_id", sa.Integer(), nullable=False),
        sa.Column("operation_id", sa.Integer(), nullable=False),
        sa.Column("row_index", sa.Integer(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("altitude", sa.Float(), nullable=True),
        sa.Column("heading", sa.Float(), nullable=True),
        sa.Column("ground_speed", sa.Float(), nullable=True),
        sa.Column("gps_latitude", sa.Float(), nullable=True),
        sa.Column("gps_longitude", sa.Float(), nullable=True),
        sa.Column("gps_altitude", sa.Float(), nullable=True),
        sa.Column("gps_ground_speed", sa.Float(), nullable=True),
        sa.Column("pitch", sa.Float(), nullable=True),
        sa.Column("roll", sa.Float(), nullable=True),
        sa.Column("pitch_rate", sa.Float(), nullable=True),
        sa.Column("roll_rate", sa.Float(), nullable=True),
        sa.Column("yaw_rate", sa.Float(), nullable=True),
        sa.Column("acceleration_x", sa.Float(), nullable=True),
        sa.Column("acceleration_y", sa.Float(), nullable=True),
        sa.Column("acceleration_z", sa.Float(), nullable=True),
        sa.Column("normalized_acceleration", sa.Float(), nullable=True),
        sa.Column("wander", sa.Float(), nullable=True),
        sa.Column("ng", sa.Float(), nullable=True),
        sa.Column("np", sa.Float(), nullable=True),
        sa.Column("nr", sa.Float(), nullable=True),
        sa.Column("torque", sa.Float(), nullable=True),
        sa.Column("mgt", sa.Float(), nullable=True),
        sa.Column("xot", sa.Float(), nullable=True),
        sa.Column("mr_speed_roc", sa.Float(), nullable=True),
        sa.Column("oat", sa.Float(), nullable=True),
        sa.Column("barometric_pressure", sa.Float(), nullable=True),
        sa.Column("pressure_altitude", sa.Float(), nullable=True),
        sa.Column("radar_altitude", sa.Float(), nullable=True),
        sa.Column("indicated_airspeed", sa.Float(), nullable=True),
        sa.Column("altitude_rate", sa.Float(), nullable=True),
        sa.Column("cpi", sa.Float(), nullable=True),
        sa.Column("wind_speed", sa.Float(), nullable=True),
        sa.Column("wind_direction", sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_fdm_state_samples_gpms_asset_id", "fdm_state_samples", ["gpms_asset_id"])
    op.create_index("ix_fdm_state_samples_operation_id", "fdm_state_samples", ["operation_id"])


def downgrade() -> None:
    op.drop_table("fdm_state_samples")
    op.drop_table("fdm_ingest_cursors")
    op.drop_table("fdm_operations")
    op.drop_table("hums_status_snapshots")
    op.drop_table("hums_status_current")
    op.drop_table("gpms_asset_mappings")
    op.drop_table("gpms_auth_tokens")
    op.drop_table("customers")
