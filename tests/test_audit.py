from datetime import datetime, timedelta

import pytest

from research_engine.audit import audit_bars
from research_engine.models import Bar


def test_audit_empty_dataset():
    result = audit_bars([])
    assert result.row_count == 0
    assert result.timezone_mode == "empty"


def test_audit_detects_interval_gaps_without_repairing():
    start = datetime(2025, 1, 1, 9, 0)
    bars = [
        Bar(start, 100, 101, 99, 100),
        Bar(start + timedelta(minutes=5), 100, 102, 99, 101),
        Bar(start + timedelta(minutes=15), 101, 103, 100, 102),
    ]
    result = audit_bars(bars, expected_interval=timedelta(minutes=5))
    assert result.row_count == 3
    assert result.interval_gap_count == 1
    assert result.largest_gap_seconds == 600
    assert result.first_timestamp.endswith("09:00:00")


def test_audit_requires_positive_interval():
    with pytest.raises(ValueError, match="positive"):
        audit_bars([], expected_interval=timedelta(0))
