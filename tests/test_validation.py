from datetime import datetime, timedelta
from research_engine.models import Bar
from research_engine.validation import validate_bars

def test_valid_bars():
    t = datetime(2025, 1, 1)
    bars = [Bar(t, 100, 102, 99, 101), Bar(t+timedelta(minutes=5), 101, 103, 100, 102)]
    assert validate_bars(bars) == []

def test_rejects_bad_ohlc():
    t = datetime(2025, 1, 1)
    assert validate_bars([Bar(t, 100, 99, 98, 101)])
