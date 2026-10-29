"""Portable raw-response archive with original-byte integrity checks."""

import base64
import gzip
import hashlib
import json
import os
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Literal
from urllib.parse import urlencode
from uuid import uuid4

Dataset = Literal["WINDFOR", "FUELHH"]
BASE_URL = "https://data.elexon.co.uk/bmrs/api/v1/datasets"
FORMAT = "winddesk_raw_archive_v1"
MAX_PAYLOAD_BYTES = 10 * 1024 * 1024
MAX_ARCHIVE_BYTES = 100 * 1024 * 1024
ATTRIBUTION = "Contains BMRS data © Elexon Limited copyright and database right 2026."
LICENCE_URL = (
    "https://www.elexon.co.uk/bsc/data/balancing-mechanism-reporting-agent/"
    "copyright-licence-bmrs-data/"
)


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def instant(value: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError("Source timestamps must be strings")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Source timestamps must include a timezone")
    return parsed.astimezone(UTC)


def iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class SourceRequest:
    dataset: Dataset
    parameters: dict[str, str]

    @property
    def url(self) -> str:
        return f"{BASE_URL}/{self.dataset}/stream?{urlencode(sorted(self.parameters.items()))}"

    @property
    def id(self) -> str:
        return digest(self.url.encode())


def january_requests() -> list[SourceRequest]:
    """Bounded, previously verified seven-day requests, with a December lookback."""
    requests = []
    start, end = datetime(2025, 12, 29, tzinfo=UTC), datetime(2026, 2, 1, tzinfo=UTC)
    while start < end:
        stop = min(start + timedelta(days=7), end)
        requests.append(
            SourceRequest(
                "WINDFOR", {"publishDateTimeFrom": iso(start), "publishDateTimeTo": iso(stop)}
            )
        )
        start = stop
    start_date, end_date = date(2026, 1, 2), date(2026, 2, 2)
    while start_date < end_date:
        stop_date = min(start_date + timedelta(days=7), end_date)
        requests.append(
            SourceRequest(
                "FUELHH",
                {
                    "settlementDateFrom": start_date.isoformat(),
                    "settlementDateTo": (stop_date - timedelta(days=1)).isoformat(),
                    "fuelType": "WIND",
                },
            )
        )
        start_date = stop_date
    return requests


@dataclass(frozen=True)
class RawBatch:
    request: SourceRequest
    received_at: datetime
    payload: bytes
    attempts: int = 1

    @property
    def payload_sha256(self) -> str:
        return digest(self.payload)

    @property
    def id(self) -> str:
        return digest(canonical([self.request.id, self.payload_sha256]))

    def rows(self) -> list[dict]:
        if len(self.payload) > MAX_PAYLOAD_BYTES:
            raise ValueError("Source response exceeds the payload limit")
        rows = json.loads(self.payload)
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            raise ValueError("Expected a top-level array of source records")
        return rows

    def document(self) -> dict:
        return {
            "dataset": self.request.dataset,
            "parameters": self.request.parameters,
            "source_url": self.request.url,
            "received_at": iso(self.received_at),
            "payload_sha256": self.payload_sha256,
            "payload_base64": base64.b64encode(self.payload).decode(),
            "response_status": 200,
            "attempts": self.attempts,
        }


def write_archive(path: Path, batches: list[RawBatch], *, complete: bool) -> None:
    document = {
        "format": FORMAT,
        "scope": "january_2026_purchase_decisions",
        "complete": complete,
        "created_at": iso(datetime.now(UTC)),
        "attribution": ATTRIBUTION,
        "licence_url": LICENCE_URL,
        "batches": [batch.document() for batch in sorted(batches, key=lambda b: b.request.id)],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        temporary.write_bytes(gzip.compress(canonical(document), mtime=0))
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def read_archive(path: Path, *, allow_partial: bool = False) -> list[RawBatch]:
    with gzip.open(path, "rb") as stream:
        content = stream.read(MAX_ARCHIVE_BYTES + 1)
    if len(content) > MAX_ARCHIVE_BYTES:
        raise ValueError("Archive exceeds the decompressed size limit")
    document = json.loads(content)
    if document.get("attribution") != ATTRIBUTION or document.get("licence_url") != LICENCE_URL:
        raise ValueError("Archive attribution or licence metadata is missing")
    if (
        document.get("format") != FORMAT
        or document.get("scope") != "january_2026_purchase_decisions"
    ):
        raise ValueError("Unsupported archive format or scope")
    if not document.get("complete") and not allow_partial:
        raise ValueError("A partial archive cannot be imported as a dataset release")
    allowed = {request.id: request for request in january_requests()}
    batches, seen = [], set()
    for entry in document["batches"]:
        request = SourceRequest(entry["dataset"], entry["parameters"])
        if request.id not in allowed or request.url != entry["source_url"] or request.id in seen:
            raise ValueError("Archive contains an unexpected or duplicate request")
        payload = base64.b64decode(entry["payload_base64"], validate=True)
        if len(payload) > MAX_PAYLOAD_BYTES or digest(payload) != entry["payload_sha256"]:
            raise ValueError("Raw payload integrity check failed")
        batch = RawBatch(request, instant(entry["received_at"]), payload, entry["attempts"])
        batch.rows()
        batches.append(batch)
        seen.add(request.id)
    if document.get("complete") and seen != set(allowed):
        raise ValueError("Complete archive is missing required request windows")
    return batches
