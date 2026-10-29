"""Create explicit source evidence and release tables. This migration is self-contained."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001_source_releases"
down_revision = None
branch_labels = None
depends_on = None

IMMUTABLE_TABLES = (
    "raw_batch",
    "forecast_version",
    "actual_version",
    "forecast_batch_member",
    "actual_batch_member",
    "dataset_release",
    "release_batch_member",
)


def upgrade() -> None:
    op.create_table(
        "ingestion_run",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("archive_sha256", sa.String(64), nullable=False),
        sa.Column("release_id", sa.String(64)),
        sa.Column("error_code", sa.String(80)),
    )
    op.create_table(
        "raw_batch",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("dataset", sa.String(8), nullable=False),
        sa.Column("source_url", sa.String(1024), nullable=False),
        sa.Column("parameters", postgresql.JSONB(), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload_sha256", sa.String(64), nullable=False),
        sa.Column("payload_gzip", sa.LargeBinary(), nullable=False),
        sa.Column("payload_bytes", sa.Integer(), nullable=False),
        sa.CheckConstraint("dataset IN ('WINDFOR', 'FUELHH')"),
    )
    for name in ("forecast_version", "actual_version"):
        extra = []
        if name == "actual_version":
            extra = [
                sa.Column("settlement_date", sa.Date(), nullable=False),
                sa.Column("settlement_period", sa.Integer(), nullable=False),
            ]
        op.create_table(
            name,
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("target_start_utc", sa.DateTime(timezone=True), nullable=False),
            sa.Column("source_published_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("generation_mw", sa.BigInteger()),
            sa.Column("quality_reason", sa.String(80)),
            *extra,
        )
        op.create_index(f"ix_{name}_target_start_utc", name, ["target_start_utc"])
        op.create_index(
            f"ix_{name}_target_publication",
            name,
            ["target_start_utc", sa.text("source_published_at DESC")],
        )
    for kind in ("forecast", "actual"):
        op.create_table(
            f"{kind}_batch_member",
            sa.Column("batch_id", sa.String(64), sa.ForeignKey("raw_batch.id"), primary_key=True),
            sa.Column(
                "version_id", sa.String(64), sa.ForeignKey(f"{kind}_version.id"), primary_key=True
            ),
        )
    op.create_table(
        "dataset_release",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("quality", postgresql.JSONB(), nullable=False),
        sa.Column("parser_version", sa.String(40), nullable=False),
        sa.CheckConstraint("status IN ('accepted', 'rejected')"),
    )
    op.create_table(
        "release_batch_member",
        sa.Column(
            "release_id", sa.String(64), sa.ForeignKey("dataset_release.id"), primary_key=True
        ),
        sa.Column("batch_id", sa.String(64), sa.ForeignKey("raw_batch.id"), primary_key=True),
    )
    op.create_table(
        "active_release",
        sa.Column("name", sa.String(32), primary_key=True),
        sa.Column("release_id", sa.String(64), sa.ForeignKey("dataset_release.id"), nullable=False),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.execute("""
        CREATE FUNCTION winddesk_reject_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN RAISE EXCEPTION 'immutable source and release data cannot be changed'; END $$;
    """)
    for name in IMMUTABLE_TABLES:
        op.execute(
            f"CREATE TRIGGER immutable_{name} BEFORE UPDATE OR DELETE ON {name} "
            "FOR EACH ROW EXECUTE FUNCTION winddesk_reject_mutation()"
        )


def downgrade() -> None:
    for name in (
        "active_release",
        "release_batch_member",
        "dataset_release",
        "actual_batch_member",
        "forecast_batch_member",
        "actual_version",
        "forecast_version",
        "raw_batch",
        "ingestion_run",
    ):
        op.drop_table(name)
    op.execute("DROP FUNCTION winddesk_reject_mutation()")
