"""Input validation. Never repairs or fabricates market data."""
from math import isfinite

from .models import Bar


def validate_bars(bars: list[Bar]) -> list[str]:
    errors: list[str] = []
    previous = None
    for i, bar in enumerate(bars):
        if previous is not None and bar.timestamp <= previous:
            errors.append(f"row {i}: timestamps must be strictly increasing")
        previous = bar.timestamp

        values = {
            "open": bar.open,
            "high": bar.high,
            "low": bar.low,
            "close": bar.close,
            "volume": bar.volume,
        }
        for name, value in values.items():
            if not isfinite(value):
                errors.append(f"row {i}: {name} must be finite")

        if all(isfinite(v) for v in (bar.open, bar.high, bar.low, bar.close)):
            if min(bar.open, bar.high, bar.low, bar.close) <= 0:
                errors.append(f"row {i}: OHLC prices must be positive")
            if bar.low > min(bar.open, bar.close) or bar.high < max(bar.open, bar.close):
                errors.append(f"row {i}: OHLC bounds invalid")
            if bar.low > bar.high:
                errors.append(f"row {i}: low exceeds high")

        if isfinite(bar.volume) and bar.volume < 0:
            errors.append(f"row {i}: negative volume")
    return errors
