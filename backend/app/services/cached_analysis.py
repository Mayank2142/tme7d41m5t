"""Cache only immutable, typed serialization; always resolve accepted release first."""

from dataclasses import dataclass
from datetime import date, time

from backend.app.cache import BoundedCache
from backend.app.persistence.reader import DatasetReader
from backend.app.services.analysis import accuracy_response, decision_response
from backend.app.services.csv_export import render_csv


@dataclass(frozen=True)
class AnalysisPayload:
    json: bytes
    csv: bytes
    context_id: str
    release_id: str
    filename: str

    @property
    def headers(self) -> dict[str, str]:
        return {"X-Analysis-Context-ID": self.context_id, "X-Dataset-Release": self.release_id}


def cached_analysis(
    cache: BoundedCache[AnalysisPayload],
    reader: DatasetReader,
    mode: str,
    start: date,
    end: date,
    cutoff: time,
    release_id: str | None,
    build: str,
) -> AnalysisPayload:
    # Do not cache this lookup: active-pointer changes and unavailable/revoked
    # releases must still be observed even when serialized facts are warm.
    release = reader.release(release_id)
    key = ("analysis-v1", mode, start, end, cutoff, release["id"], release["parser_version"], build)

    def load():
        if mode == "decision":
            result = decision_response(
                reader, start, cutoff, release["id"], build, resolved_release=release
            )
        else:
            result = accuracy_response(
                reader, start, end, cutoff, release["id"], build, resolved_release=release
            )
        filename = f"winddesk-{mode}-{start}-{end}-{result.analysis_context_id[:12]}.csv"
        return AnalysisPayload(
            result.model_dump_json().encode("utf-8"),
            render_csv(result).encode("utf-8"),
            result.analysis_context_id,
            release["id"],
            filename,
        )

    return cache.get(key, load, lambda payload: len(payload.json) + len(payload.csv) + 1024)
