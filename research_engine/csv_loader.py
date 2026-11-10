"""Strict CSV ingestion for OHLCV bars.

The loader never repairs rows, interpolates gaps, or silently drops malformed
records. Naive timestamps are interpreted in the configured market timezone.
"""
import csv
from datetime import datetime
from pathlib import Path
from math import isfinite
from typing import IO

from .models import Bar
from .validation import validate_bars

DEFAULT_COLUMNS = {
    "timestamp": ("timestamp", "datetime", "date_time", "time", "日期時間", "時間"),
    "open": ("open", "開盤", "開盤價"),
    "high": ("high", "最高", "最高價"),
    "low": ("low", "最低", "最低價"),
    "close": ("close", "收盤", "收盤價"),
    "volume": ("volume", "vol", "成交量"),
}


def _parse_timestamp(value: str, row_number: int) -> datetime:
    raw = value.strip()
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"row {row_number}: unsupported timestamp {raw!r}; use ISO-8601") from exc


def _parse_number(value: str, field: str, row_number: int) -> float:
    try:
        number = float(value.replace(",", "").strip())
    except (AttributeError, ValueError) as exc:
        raise ValueError(f"row {row_number}: invalid {field} value {value!r}") from exc
    if not isfinite(number):
        raise ValueError(f"row {row_number}: {field} must be finite")
    return number


def load_bars_csv(
    source: str | Path | IO[str],
    *,
    columns: dict[str, str] | None = None,
    require_volume: bool = True,
) -> list[Bar]:
    """Load and validate CSV rows using explicit or common column names.

    columns maps canonical names (timestamp/open/high/low/close/volume) to
    exact CSV headers. If omitted, common English and Traditional Chinese
    headers are detected case-insensitively. All malformed rows are fatal.
    """
    close_after = False
    if isinstance(source, (str, Path)):
        handle = Path(source).open("r", encoding="utf-8-sig", newline="")
        close_after = True
    else:
        handle = source

    try:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError("CSV has no header row")
        headers = {name.strip().lower(): name for name in reader.fieldnames if name}
        resolved: dict[str, str] = {}
        for field, aliases in DEFAULT_COLUMNS.items():
            explicit = columns.get(field) if columns else None
            match = explicit if explicit in reader.fieldnames else None
            if match is None and explicit is not None:
                raise ValueError(f"CSV is missing configured column {explicit!r}")
            if match is None:
                match = next((headers[a.lower()] for a in aliases if a.lower() in headers), None)
            if match is not None:
                resolved[field] = match

        required = ["timestamp", "open", "high", "low", "close"]
        if require_volume:
            required.append("volume")
        missing = [field for field in required if field not in resolved]
        if missing:
            raise ValueError(f"CSV missing required columns: {', '.join(missing)}")

        bars: list[Bar] = []
        for row_number, row in enumerate(reader, start=2):
            if not row or all(value is None or not value.strip() for value in row.values()):
                raise ValueError(f"row {row_number}: blank rows are not allowed")
            timestamp = _parse_timestamp(row[resolved["timestamp"]], row_number)
            values = {
                field: _parse_number(row[resolved[field]], field, row_number)
                for field in ("open", "high", "low", "close")
            }
            volume = _parse_number(row[resolved["volume"]], "volume", row_number) if "volume" in resolved else 0.0
            bars.append(Bar(timestamp=timestamp, volume=volume, **values))

        errors = validate_bars(bars)
        if errors:
            raise ValueError("CSV validation failed: " + "; ".join(errors[:20]))
        return bars
    finally:
        if close_after:
            handle.close()
