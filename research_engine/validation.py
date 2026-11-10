"""Input validation. Never repairs or fabricates market data."""
from .models import Bar

def validate_bars(bars: list[Bar]) -> list[str]:
    errors: list[str] = []
    previous = None
    for i, bar in enumerate(bars):
        if previous is not None and bar.timestamp <= previous:
            errors.append(f"row {i}: timestamps must be strictly increasing")
        previous = bar.timestamp
        if bar.low > min(bar.open, bar.close) or bar.high < max(bar.open, bar.close):
            errors.append(f"row {i}: OHLC bounds invalid")
        if bar.low > bar.high:
            errors.append(f"row {i}: low exceeds high")
        if bar.volume < 0:
            errors.append(f"row {i}: negative volume")
    return errors
