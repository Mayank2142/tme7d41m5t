"""One analysis path for JSON and CSV; pin a release before reading any facts."""

import hashlib
import json
from datetime import date, time
from urllib.parse import urlencode

from backend.app.contracts import (
    AccuracyContext,
    AccuracyResponse,
    AccuracySource,
    DecisionContext,
    DecisionResponse,
    DecisionSource,
)
from backend.app.domain.analysis import analyze_accuracy, analyze_decision
from backend.app.persistence.reader import DatasetReader


def context_identity(context: DecisionContext | AccuracyContext) -> str:
    content = json.dumps(
        context.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(content).hexdigest()


def _export_url(context: DecisionContext | AccuracyContext, context_id: str) -> str:
    params = {
        "mode": context.mode,
        "release_id": context.release_id,
        "cutoff_local": context.cutoff_local,
        "expected_context_id": context_id,
    }
    if context.mode == "decision":
        params["decision_date"] = context.decision_from.isoformat()
    else:
        params.update(
            decision_from=context.decision_from.isoformat(),
            decision_to=context.decision_to.isoformat(),
            comparison_policy=context.comparison_policy,
        )
    return "/api/v1/export.csv?" + urlencode(params)


def decision_response(
    reader: DatasetReader,
    day: date,
    cutoff: time,
    release_id: str | None,
    build_sha: str,
) -> DecisionResponse:
    release = reader.release(release_id)
    pinned_id = release["id"]
    # Do not even load actuals for a decision replay.
    result = analyze_decision(reader.forecasts(pinned_id), day, cutoff)
    context = DecisionContext(
        release_id=pinned_id,
        source_parser=release["parser_version"],
        build_sha=build_sha,
        decision_from=day,
        decision_to=day,
        cutoff_local=result.window.cutoff_local,
    )
    context_id = context_identity(context)
    return DecisionResponse(
        analysis_context_id=context_id,
        context=context,
        analysis=result,
        source=DecisionSource(data_quality_url=f"/api/v1/data-quality?release_id={pinned_id}"),
        export_url=_export_url(context, context_id),
    )


def accuracy_response(
    reader: DatasetReader,
    start: date,
    end: date,
    cutoff: time,
    release_id: str | None,
    build_sha: str,
) -> AccuracyResponse:
    release = reader.release(release_id)
    pinned_id = release["id"]
    result = analyze_accuracy(
        reader.forecasts(pinned_id), reader.actuals(pinned_id), start, end, cutoff
    )
    context = AccuracyContext(
        release_id=pinned_id,
        source_parser=release["parser_version"],
        build_sha=build_sha,
        decision_from=start,
        decision_to=end,
        cutoff_local=result.cutoff_local,
    )
    context_id = context_identity(context)
    return AccuracyResponse(
        analysis_context_id=context_id,
        context=context,
        analysis=result,
        source=AccuracySource(data_quality_url=f"/api/v1/data-quality?release_id={pinned_id}"),
        export_url=_export_url(context, context_id),
    )
