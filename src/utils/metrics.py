"""Lightweight in-process metrics for observability.

This module provides simple counters and timing statistics without external
dependencies so it can be used in unit tests and simple deployments.
"""

from __future__ import annotations

import statistics
import threading

# Minimum number of samples required for accurate p95 percentile calculation
_MIN_SAMPLES_FOR_P95 = 20

_lock = threading.Lock()
_counters: dict[str, int] = {}
_timings: dict[str, list[float]] = {}


def incr(metric: str, amount: int = 1) -> None:
    """Increment a named counter by `amount`."""
    with _lock:
        _counters[metric] = _counters.get(metric, 0) + int(amount)


def timing(metric: str, value_ms: float) -> None:
    """Record a timing value (milliseconds) for a named metric."""
    with _lock:
        _timings.setdefault(metric, []).append(float(value_ms))


def get_metrics() -> dict:
    """Return a snapshot of current metrics (counters and timing summaries)."""
    with _lock:
        counters = dict(_counters)
        timings = {k: list(v) for k, v in _timings.items()}

    timing_stats = {}
    for name, values in timings.items():
        if not values:
            continue
        timing_stats[name] = {
            "count": len(values),
            "min_ms": min(values),
            "max_ms": max(values),
            "mean_ms": statistics.mean(values),
            "p95_ms": statistics.quantiles(values, n=100)[94]
            if len(values) >= _MIN_SAMPLES_FOR_P95
            else max(values),
        }

    return {"counters": counters, "timings": timing_stats}


def reset_metrics() -> None:
    """Reset all metrics (useful for tests)."""
    with _lock:
        _counters.clear()
        _timings.clear()
