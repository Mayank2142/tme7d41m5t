"""Small bounded HTTP client with resumable raw-archive downloads."""

import random
import time
from collections.abc import Callable
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path

import httpx2 as httpx

from backend.app.ingestion.archive import (
    BASE_URL,
    MAX_PAYLOAD_BYTES,
    RawBatch,
    SourceRequest,
    january_requests,
    read_archive,
    write_archive,
)


class SourceError(RuntimeError):
    pass


class ElexonClient:
    def __init__(self, client: httpx.Client | None = None, sleep: Callable = time.sleep):
        self.client = client or httpx.Client(
            timeout=httpx.Timeout(30, connect=5, pool=5),
            follow_redirects=False,
            headers={"Accept": "application/json", "User-Agent": "WindDesk-assignment/0.2"},
        )
        self.owns_client = client is None
        self.sleep = sleep

    def close(self) -> None:
        if self.owns_client:
            self.client.close()

    def fetch(self, request: SourceRequest) -> RawBatch:
        if request.dataset not in {"WINDFOR", "FUELHH"} or not request.url.startswith(
            BASE_URL + "/"
        ):
            raise ValueError("Only the approved Elexon sources are permitted")
        for attempt in range(4):
            delay = min(2**attempt, 8)
            try:
                with self.client.stream("GET", request.url) as response:
                    if response.status_code == 429 or response.status_code >= 500:
                        header = response.headers.get("Retry-After")
                        if header:
                            try:
                                delay = float(header)
                            except ValueError:
                                delay = max(
                                    0,
                                    (
                                        parsedate_to_datetime(header) - datetime.now(UTC)
                                    ).total_seconds(),
                                )
                        if attempt == 3 or delay > 30:
                            raise SourceError(
                                f"Upstream temporarily unavailable: HTTP {response.status_code}"
                            )
                    elif response.status_code != 200:
                        raise SourceError(f"Upstream request rejected: HTTP {response.status_code}")
                    else:
                        pieces, size = [], 0
                        for piece in response.iter_bytes():
                            size += len(piece)
                            if size > MAX_PAYLOAD_BYTES:
                                raise SourceError(
                                    "Upstream response exceeded the configured size limit"
                                )
                            pieces.append(piece)
                        batch = RawBatch(request, datetime.now(UTC), b"".join(pieces), attempt + 1)
                        batch.rows()
                        return batch
            except httpx.TransportError as exc:
                if attempt == 3:
                    raise SourceError("Upstream transport failed after bounded retries") from exc
            self.sleep(max(0, delay) + random.uniform(0, 0.25))
        raise SourceError("Upstream retry limit exhausted")


def download_january(
    path: Path,
    *,
    refresh: bool = False,
    client: ElexonClient | None = None,
    progress: Callable = print,
) -> list[RawBatch]:
    checkpoint = path.with_suffix(path.suffix + ".partial")
    if path.exists() and not refresh:
        return read_archive(path)
    existing = (
        read_archive(checkpoint, allow_partial=True) if checkpoint.exists() and not refresh else []
    )
    batches = {batch.request.id: batch for batch in existing}
    source = client or ElexonClient()
    try:
        for request in january_requests():
            if request.id not in batches:
                batch = source.fetch(request)
                batches[request.id] = batch
                write_archive(checkpoint, list(batches.values()), complete=False)
                progress(
                    f"{request.dataset}: archived window {len(batches)}/{len(january_requests())}"
                )
        result = list(batches.values())
        write_archive(path, result, complete=True)
        checkpoint.unlink(missing_ok=True)
        return result
    finally:
        if client is None:
            source.close()
