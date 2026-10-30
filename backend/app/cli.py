"""Operator entry points for serving, ingestion, recovery, and analysis verification."""

import argparse
import json
import logging
import os
from dataclasses import asdict
from datetime import date, datetime
from pathlib import Path

import uvicorn
from sqlalchemy.exc import SQLAlchemyError

from backend.app.config import Settings
from backend.app.domain.analysis import analyze_accuracy
from backend.app.domain.calendar import parse_cutoff
from backend.app.ingestion.archive import ATTRIBUTION, LICENCE_URL, iso, read_archive
from backend.app.ingestion.client import SourceError, download_january
from backend.app.ingestion.validation import inspect_batches, release_identity
from backend.app.persistence.analysis import load_analysis_sources
from backend.app.persistence.database import create_database_engine, database_available
from backend.app.persistence.migrate import migrate
from backend.app.persistence.permissions import configure_reader
from backend.app.persistence.releases import dataset_state, export_archive, import_archive

DEFAULT_ARCHIVE = Path("data/snapshots/january_2026.json.gz")


def _json_default(value):
    if isinstance(value, datetime):
        return iso(value)
    if isinstance(value, date):
        return value.isoformat()
    raise TypeError(f"Unsupported JSON value: {type(value).__name__}")


def manifest(path: Path, report_path: Path | None = None, *, allow_partial: bool = False) -> dict:
    batches = read_archive(path)
    quality, _ = inspect_batches(batches)
    quality["acceptance_policy"] = "allow_partial_v1" if allow_partial else "strict_v1"
    result = {
        "release_id": release_identity(batches, quality),
        "quality": quality,
        "attribution": ATTRIBUTION,
        "licence_url": LICENCE_URL,
        "raw_batches": [
            {
                "id": batch.id,
                "dataset": batch.request.dataset,
                "source_url": batch.request.url,
                "received_at": iso(batch.received_at),
                "sha256": batch.payload_sha256,
                "bytes": len(batch.payload),
            }
            for batch in sorted(batches, key=lambda batch: batch.id)
        ],
    }
    if report_path:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def _run() -> None:
    parser = argparse.ArgumentParser(prog="winddesk")
    commands = parser.add_subparsers(dest="command", required=True)
    server = commands.add_parser("serve", help="Run the API and any compiled frontend")
    server.add_argument("--host", default="127.0.0.1")
    server.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8000")))
    server.add_argument("--reload", action="store_true")
    commands.add_parser(
        "check-db", help="Check PostgreSQL connectivity without exposing credentials"
    )
    commands.add_parser("migrate", help="Apply checked-in PostgreSQL migrations")
    for name in ("fetch", "validate", "seed", "backfill"):
        command = commands.add_parser(name)
        command.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE)
        if name in {"fetch", "backfill"}:
            command.add_argument("--refresh", action="store_true")
        if name in {"seed", "backfill"}:
            command.add_argument("--allow-partial", action="store_true")
            command.add_argument("--configure-reader", action="store_true")
        if name in {"validate", "seed", "backfill"}:
            command.add_argument("--report", type=Path)
    export = commands.add_parser(
        "export-release", help="Recover a raw archive from a database release"
    )
    export.add_argument("--release-id")
    export.add_argument("--output", type=Path, required=True)
    analysis = commands.add_parser("analyze", help="Verify retrospective source-time accuracy")
    analysis.add_argument("--decision-from", type=date.fromisoformat, default=date(2026, 1, 1))
    analysis.add_argument("--decision-to", type=date.fromisoformat, default=date(2026, 1, 31))
    analysis.add_argument("--cutoff", type=parse_cutoff)
    analysis.add_argument("--release-id")
    analysis.add_argument(
        "--output", type=Path, help="Write all selected points and coverage to JSON"
    )
    args = parser.parse_args()
    if args.command == "serve":
        settings = Settings()
        if args.reload and settings.web_workers > 1:
            parser.error("Reload mode requires GRID_WEB_WORKERS=1")
        logging.basicConfig(level=logging.INFO, format="%(message)s")
        uvicorn.run(
            "backend.app.main:create_app",
            factory=True,
            host=args.host,
            port=args.port,
            reload=args.reload,
            workers=settings.web_workers,
            proxy_headers=bool(settings.trusted_proxy_ips),
            forwarded_allow_ips=",".join(settings.trusted_proxy_ips),
            server_header=False,
            timeout_keep_alive=5,
            timeout_graceful_shutdown=20,
        )
    elif args.command in {"fetch", "validate"}:
        if args.command == "fetch":
            download_january(args.archive, refresh=args.refresh)
        result = manifest(
            args.archive,
            args.report if args.command == "validate" else args.archive.with_name("manifest.json"),
        )
        print(
            json.dumps(
                {
                    "release_id": result["release_id"],
                    "quality": {
                        key: value for key, value in result["quality"].items() if key != "decisions"
                    },
                }
            )
        )
        raise SystemExit(0 if result["quality"]["status"] == "complete" else 1)
    else:
        engine = create_database_engine(Settings())
        try:
            if args.command == "check-db":
                available = database_available(engine)
                print(json.dumps({"database": "available" if available else "unavailable"}))
                raise SystemExit(0 if available else 1)
            if args.command in {"migrate", "seed", "backfill"}:
                migrate(engine)
            if args.command == "migrate":
                print(json.dumps({"schema": "0002_freeze_release_versions"}))
            elif args.command in {"seed", "backfill"}:
                if args.command == "backfill":
                    download_january(args.archive, refresh=args.refresh)
                result = import_archive(engine, args.archive, allow_partial=args.allow_partial)
                if args.configure_reader:
                    reader_url = Settings().reader_database_url
                    if reader_url is None:
                        raise ValueError("Set GRID_READER_DATABASE_URL to provision the web login")
                    configure_reader(engine, reader_url.get_secret_value())
                if args.report:
                    manifest(args.archive, args.report, allow_partial=args.allow_partial)
                print(
                    json.dumps(
                        {
                            "release_id": result["release_id"],
                            "accepted": result["accepted"],
                            "quality_status": result["quality"]["status"],
                        }
                    )
                )
                raise SystemExit(0 if result["accepted"] else 1)
            elif args.command == "export-release":
                state = dataset_state(engine)
                release_id = args.release_id or (state.release["id"] if state.release else None)
                if not release_id:
                    raise ValueError("No active release exists")
                export_archive(engine, release_id, args.output)
                print(json.dumps({"exported_release": release_id, "path": str(args.output)}))
            elif args.command == "analyze":
                settings = Settings()
                sources = load_analysis_sources(engine, args.release_id)
                result = analyze_accuracy(
                    sources.forecasts,
                    sources.actuals,
                    args.decision_from,
                    args.decision_to,
                    args.cutoff or settings.default_cutoff_local,
                )
                metadata = {
                    "release_id": sources.release_id,
                    "source_parser": sources.parser_version,
                    "build_sha": settings.build_sha,
                    "attribution": ATTRIBUTION,
                    "licence_url": LICENCE_URL,
                }
                if args.output:
                    args.output.parent.mkdir(parents=True, exist_ok=True)
                    args.output.write_text(
                        json.dumps(
                            metadata | {"analysis": asdict(result)},
                            default=_json_default,
                            indent=2,
                            allow_nan=False,
                        )
                        + "\n",
                        encoding="utf-8",
                    )
                print(
                    json.dumps(
                        metadata
                        | {
                            "decision_from": result.decision_from,
                            "decision_to": result.decision_to,
                            "cutoff_local": result.cutoff_local,
                            "comparison_policy": result.comparison_policy,
                            "metrics": asdict(result.metrics),
                            "coverage": asdict(result.coverage),
                            "actual_source_coverage": asdict(result.actual_source_coverage),
                        },
                        default=_json_default,
                        allow_nan=False,
                    )
                )
        finally:
            engine.dispose()


def main() -> None:
    try:
        _run()
    except (SQLAlchemyError, OSError) as exc:
        print(
            json.dumps(
                {
                    "error": type(exc).__name__,
                    "message": "Check database connectivity, migrations, and file access",
                }
            )
        )
        raise SystemExit(2) from None
    except (ValueError, SourceError) as exc:
        print(json.dumps({"error": type(exc).__name__, "message": str(exc)}))
        raise SystemExit(2) from None


if __name__ == "__main__":
    main()
