"""Freeze parsed version membership independently of later parses of the same raw batch."""

import sqlalchemy as sa
from alembic import op

revision = "0002_freeze_release_versions"
down_revision = "0001_source_releases"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for kind in ("forecast", "actual"):
        name = f"release_{kind}_member"
        op.create_table(
            name,
            sa.Column(
                "release_id", sa.String(64), sa.ForeignKey("dataset_release.id"), primary_key=True
            ),
            sa.Column(
                "version_id", sa.String(64), sa.ForeignKey(f"{kind}_version.id"), primary_key=True
            ),
        )
        op.execute(f"""
            INSERT INTO {name} (release_id, version_id)
            SELECT DISTINCT r.release_id, m.version_id
            FROM release_batch_member r
            JOIN {kind}_batch_member m ON m.batch_id = r.batch_id
        """)
        op.execute(
            f"CREATE TRIGGER immutable_{name} BEFORE UPDATE OR DELETE ON {name} "
            "FOR EACH ROW EXECUTE FUNCTION winddesk_reject_mutation()"
        )


def downgrade() -> None:
    op.drop_table("release_actual_member")
    op.drop_table("release_forecast_member")
