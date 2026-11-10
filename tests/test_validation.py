from datetime import datetime, timedelta

from research_engine.models import Bar
from research_engine.validation import validate_bars


def test_valid_bars():
    t = datetime(2025, 1, 1)
    bars = [Bar(t, 100, 102, 99, 101), Bar(t + timedelta(minutes=5), 101, 103, 100, 102)]
    assert validate_bars(bars) == []


def test_rejects_bad_ohlc():
    t = datetime(2025, 1, 1)
    assert validate_bars([Bar(t, 100, 99, 98, 101)])


def test_rejects_duplicate_timestamps_and_negative_volume():
    t = datetime(2025, 1, 1)
    bars = [Bar(t, 100, 102, 99, 101, 1), Bar(t, 101, 103, 100, 102, -1)]
    errors = validate_bars(bars)
    assert any("strictly increasing" in error for error in errors)
    assert any("negative volume" in error for error in errors)


def test_rejects_non_finite_prices():
    t = datetime(2025, 1, 1)
    bars = [Bar(t, float("nan"), 102, 99, 101)]
    assert any("must be finite" in error for error in validate_bars(bars))
