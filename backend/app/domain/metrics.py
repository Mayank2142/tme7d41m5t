"""Versioned descriptive errors: source-time MW, no inference or energy conversion."""

from collections.abc import Iterable
from dataclasses import dataclass
from math import fsum, sqrt

METRICS_VERSION = "metrics_v1"


@dataclass(frozen=True)
class ErrorMetrics:
    paired_targets: int
    mae_mw: float | None
    rmse_mw: float | None
    bias_mw: float | None
    p90_absolute_error_mw: float | None
    reason: str | None
    version: str = METRICS_VERSION
    unit: str = "MW"


def error_metrics(errors_mw: Iterable[int]) -> ErrorMetrics:
    """P90 uses linear interpolation at sorted index (n - 1) * 0.9."""
    errors = tuple(errors_mw)
    if any(isinstance(value, bool) or not isinstance(value, int) for value in errors):
        raise ValueError("Source-time errors must be integer MW values")
    n = len(errors)
    if not n:
        return ErrorMetrics(0, None, None, None, None, "NO_VALID_PAIRS")
    absolute = sorted(abs(value) for value in errors)
    # Integer rank arithmetic prevents floating-point rank drift at exact deciles.
    lower, remainder = divmod((n - 1) * 9, 10)
    p90 = float(absolute[lower])
    if remainder:
        p90 += (absolute[lower + 1] - absolute[lower]) * (remainder / 10)
    return ErrorMetrics(
        n,
        fsum(absolute) / n,
        sqrt(fsum(value * value for value in errors) / n),
        fsum(errors) / n,
        p90,
        None,
    )
