from io import StringIO

import pytest

from research_engine.csv_loader import load_bars_csv


def test_loads_traditional_chinese_headers():
    csv_text = (
        "時間,開盤價,最高價,最低價,收盤價,成交量\n"
        "2025-01-01T09:00:00,100,102,99,101,120\n"
        "2025-01-01T09:05:00,101,103,100,102,135\n"
    )
    bars = load_bars_csv(StringIO(csv_text))
    assert len(bars) == 2
    assert bars[0].open == 100
    assert bars[1].volume == 135


def test_explicit_column_mapping():
    csv_text = "ts,o,h,l,c,v\n2025-01-01T09:00:00,100,102,99,101,10\n"
    bars = load_bars_csv(
        StringIO(csv_text),
        columns={"timestamp": "ts", "open": "o", "high": "h", "low": "l", "close": "c", "volume": "v"},
    )
    assert bars[0].close == 101


def test_rejects_missing_volume_by_default():
    csv_text = "timestamp,open,high,low,close\n2025-01-01T09:00:00,100,102,99,101\n"
    with pytest.raises(ValueError, match="volume"):
        load_bars_csv(StringIO(csv_text))


def test_rejects_malformed_numeric_value():
    csv_text = "timestamp,open,high,low,close,volume\n2025-01-01T09:00:00,nope,102,99,101,10\n"
    with pytest.raises(ValueError, match="open"):
        load_bars_csv(StringIO(csv_text))


def test_rejects_duplicate_or_unsorted_timestamps():
    csv_text = (
        "timestamp,open,high,low,close,volume\n"
        "2025-01-01T09:05:00,100,102,99,101,10\n"
        "2025-01-01T09:00:00,101,103,100,102,10\n"
    )
    with pytest.raises(ValueError, match="strictly increasing"):
        load_bars_csv(StringIO(csv_text))
