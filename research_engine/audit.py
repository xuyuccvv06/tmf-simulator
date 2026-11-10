"""Non-destructive audit summaries for already-loaded market bars."""
from dataclasses import dataclass
from datetime import timedelta

from .models import Bar
from .validation import validate_bars


@dataclass(frozen=True)
class DataAudit:
    row_count: int
    first_timestamp: str | None
    last_timestamp: str | None
    timezone_mode: str
    validation_errors: tuple[str, ...]
    interval_gap_count: int
    largest_gap_seconds: float
    non_standard_intervals: int


def audit_bars(bars: list[Bar], *, expected_interval: timedelta | None = None) -> DataAudit:
    """Summarize data without repairing, dropping, or filling any records.

    If expected_interval is supplied, timestamp differences larger than that
    interval are counted as gaps; this is a mechanical interval check only.
    Exchange closures and session boundaries must be filtered/interpreted by
    a separately verified exchange calendar before treating gaps as defects.
    """
    errors = tuple(validate_bars(bars))
    if not bars:
        return DataAudit(0, None, None, "empty", errors, 0, 0.0, 0)

    aware = [bar.timestamp.utcoffset() is not None for bar in bars]
    timezone_mode = "aware" if all(aware) else "naive" if not any(aware) else "mixed"
    gaps = 0
    largest = 0.0
    non_standard = 0
    if expected_interval is not None:
        if expected_interval.total_seconds() <= 0:
            raise ValueError("expected_interval must be positive")
        for previous, current in zip(bars, bars[1:]):
            seconds = (current.timestamp - previous.timestamp).total_seconds()
            if seconds > expected_interval.total_seconds():
                gaps += 1
                largest = max(largest, seconds)
            elif seconds != expected_interval.total_seconds():
                non_standard += 1

    return DataAudit(
        row_count=len(bars),
        first_timestamp=bars[0].timestamp.isoformat(),
        last_timestamp=bars[-1].timestamp.isoformat(),
        timezone_mode=timezone_mode,
        validation_errors=errors,
        interval_gap_count=gaps,
        largest_gap_seconds=largest,
        non_standard_intervals=non_standard,
    )
