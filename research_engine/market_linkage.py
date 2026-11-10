"""Link journal events to immutable dataset bars without inferring trading rules."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

from .models import Bar


@dataclass(frozen=True)
class MarketReference:
    dataset_id: str
    dataset_sha256: str
    timeframe: str
    start_timestamp: str
    end_timestamp: str


def _parse(value: str, field: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as exc:
        raise ValueError(f"{field} must be an ISO-8601 timestamp") from exc


def create_market_reference(
    *,
    dataset_id: str,
    dataset_sha256: str,
    timeframe: str,
    start_timestamp: str,
    end_timestamp: str,
) -> dict[str, str]:
    """Build a provenance-bound time window; timestamps are not rounded."""
    if not dataset_id.strip():
        raise ValueError("dataset_id is required")
    if len(dataset_sha256) != 64 or any(c not in "0123456789abcdef" for c in dataset_sha256.lower()):
        raise ValueError("dataset_sha256 must be a 64-character SHA-256 hex digest")
    if not timeframe.strip():
        raise ValueError("timeframe is required")
    start = _parse(start_timestamp, "start_timestamp")
    end = _parse(end_timestamp, "end_timestamp")
    if start.tzinfo != end.tzinfo or start.utcoffset() != end.utcoffset():
        raise ValueError("start and end timestamps must use the same timezone basis")
    if end < start:
        raise ValueError("end_timestamp must be >= start_timestamp")
    return {
        "dataset_id": dataset_id,
        "dataset_sha256": dataset_sha256.lower(),
        "timeframe": timeframe,
        "start_timestamp": start.isoformat(),
        "end_timestamp": end.isoformat(),
    }


def resolve_market_reference(
    *,
    reference: dict[str, str],
    bars: Iterable[Bar],
    dataset_id: str,
    dataset_sha256: str,
) -> list[Bar]:
    """Resolve only exact bar timestamps against the declared dataset identity.

    No interpolation, nearest-bar matching, timestamp rounding, or gap filling
    is performed. A dataset identity mismatch is always an error.
    """
    if reference.get("dataset_id") != dataset_id:
        raise ValueError("dataset_id does not match market reference")
    if reference.get("dataset_sha256", "").lower() != dataset_sha256.lower():
        raise ValueError("dataset_sha256 does not match market reference")
    start = _parse(reference.get("start_timestamp"), "start_timestamp")
    end = _parse(reference.get("end_timestamp"), "end_timestamp")
    source = list(bars)
    selected = [bar for bar in source if start <= bar.timestamp <= end]
    if not selected:
        raise LookupError("no bars found inside the referenced market time window")
    if selected[0].timestamp != start or selected[-1].timestamp != end:
        raise LookupError("reference boundaries must match exact dataset bar timestamps")
    return selected
