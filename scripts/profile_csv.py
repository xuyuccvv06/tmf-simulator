"""Read-only structural and OHLCV audit for the checked-in TMFR1 CSV."""
from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from datetime import datetime
from math import isfinite
from pathlib import Path

from research_engine.session_audit import classify_tmfr1_interval
from research_engine.calendar_audit import classify_overnight_gap, load_closures


ALIASES = {
    "timestamp": ("datetime", "timestamp", "時間", "日期時間"),
    "open": ("open", "開盤價", "開盤"),
    "high": ("high", "最高價", "最高"),
    "low": ("low", "最低價", "最低"),
    "close": ("close", "收盤價", "收盤"),
    "volume": ("volume", "成交量", "vol"),
}


def open_text(path: Path):
    failures = []
    for encoding in ("utf-8-sig", "cp950", "big5"):
        try:
            handle = path.open("r", encoding=encoding, newline="")
            handle.read(4096)
            handle.seek(0)
            return handle, encoding
        except UnicodeDecodeError as exc:
            failures.append(f"{encoding}: {exc}")
    raise UnicodeError("Unable to decode CSV: " + " | ".join(failures))


def profile(path: Path) -> dict:
    handle, encoding = open_text(path)
    with handle:
        sample = handle.read(8192)
        handle.seek(0)
        try:
            delimiter = csv.Sniffer().sniff(sample, delimiters=",;\t|").delimiter
        except csv.Error:
            delimiter = ","
        reader = csv.DictReader(handle, delimiter=delimiter)
        if not reader.fieldnames:
            raise ValueError("CSV is empty or has no header")
        headers = reader.fieldnames
        normalized = {name.strip().lower(): name for name in headers if name}
        resolved = {}
        for field, aliases in ALIASES.items():
            match = next((normalized[a] for a in aliases if a in normalized), None)
            if match:
                resolved[field] = match
        missing = [name for name in ALIASES if name not in resolved]
        if missing:
            raise ValueError(f"Missing required columns for audit: {missing}")

        row_count = blank_rows = malformed_width = numeric_errors = timestamp_errors = 0
        ohlc_errors = negative_volume = duplicate_timestamps = out_of_order = 0
        first_timestamp = last_timestamp = previous_timestamp = None
        min_prices = {k: None for k in ("open", "high", "low", "close")}
        max_prices = {k: None for k in ("open", "high", "low", "close")}
        interval_counts = Counter()
        interval_examples = {}
        interval_classes = Counter()
        calendar_gap_classes = Counter()
        calendar_gap_examples = []
        closures = load_closures("data/calendars/taifex_market_closures_2024_2025.csv")
        unexpected_examples = []
        first_rows = []
        trading_dates = set()
        daily_coverage = {}
        previous_trading_date = None
        date_column = normalized.get("trading_date")

        for row in reader:
            row_count += 1
            if None in row:
                malformed_width += 1
            if not row or all(v is None or not str(v).strip() for v in row.values()):
                blank_rows += 1
                continue
            try:
                ts = datetime.fromisoformat(row[resolved["timestamp"]].strip().replace("Z", "+00:00"))
            except (ValueError, TypeError):
                timestamp_errors += 1
                continue
            if first_timestamp is None:
                first_timestamp = ts.isoformat(sep=" ")
            current_trading_date = row.get(date_column) if date_column else None
            if previous_timestamp is not None:
                delta = (ts - previous_timestamp).total_seconds()
                if delta == 0:
                    duplicate_timestamps += 1
                elif delta < 0:
                    out_of_order += 1
                else:
                    key = str(int(delta))
                    interval_counts[key] += 1
                    classification = classify_tmfr1_interval(previous_timestamp, ts)
                    interval_classes[classification] += 1
                    if classification == "after_hours_to_day":
                        calendar_result = classify_overnight_gap(previous_timestamp, ts, closures)
                        calendar_label = str(calendar_result["classification"])
                        calendar_gap_classes[calendar_label] += 1
                        if len(calendar_gap_examples) < 400:
                            calendar_gap_examples.append({
                                "previous_timestamp": previous_timestamp.isoformat(sep=" "),
                                "current_timestamp": ts.isoformat(sep=" "),
                                **calendar_result,
                            })
                    if classification == "unexpected_interval" and len(unexpected_examples) < 50:
                        unexpected_examples.append({
                            "previous_timestamp": previous_timestamp.isoformat(sep=" "),
                            "current_timestamp": ts.isoformat(sep=" "),
                            "delta_seconds": int(delta),
                        })
                    examples = interval_examples.setdefault(key, [])
                    if len(examples) < 8:
                        examples.append({
                            "previous_timestamp": previous_timestamp.isoformat(sep=" "),
                            "previous_trading_date": previous_trading_date,
                            "current_timestamp": ts.isoformat(sep=" "),
                            "current_trading_date": current_trading_date,
                        })
            previous_timestamp = ts
            previous_trading_date = current_trading_date
            last_timestamp = ts.isoformat(sep=" ")
            values = {}
            try:
                for field in ("open", "high", "low", "close", "volume"):
                    raw = row[resolved[field]]
                    value = float(raw.replace(",", "").strip())
                    if not isfinite(value):
                        raise ValueError(field)
                    values[field] = value
            except (ValueError, TypeError, AttributeError, KeyError):
                numeric_errors += 1
                continue
            o, h, l, close = (values[k] for k in ("open", "high", "low", "close"))
            if min(o, h, l, close) <= 0 or h < max(o, l, close) or l > min(o, h, close):
                ohlc_errors += 1
            if values["volume"] < 0:
                negative_volume += 1
            for field in min_prices:
                value = values[field]
                min_prices[field] = value if min_prices[field] is None else min(min_prices[field], value)
                max_prices[field] = value if max_prices[field] is None else max(max_prices[field], value)
            if date_column and row.get(date_column):
                trading_date = row[date_column]
                trading_dates.add(trading_date)
                bucket = daily_coverage.setdefault(trading_date, {
                    "total": 0, "day": 0, "night": 0,
                    "first_timestamp": ts.isoformat(sep=" "),
                    "last_timestamp": ts.isoformat(sep=" "),
                    "day_first": None, "day_last": None,
                    "night_first": None, "night_last": None,
                })
                bucket["total"] += 1
                clock = ts.time().replace(tzinfo=None)
                if clock >= datetime.strptime("08:45", "%H:%M").time() and clock < datetime.strptime("13:45", "%H:%M").time():
                    bucket["day"] += 1
                    bucket["day_first"] = bucket["day_first"] or ts.isoformat(sep=" ")
                    bucket["day_last"] = ts.isoformat(sep=" ")
                elif clock >= datetime.strptime("15:00", "%H:%M").time() or clock < datetime.strptime("05:00", "%H:%M").time():
                    bucket["night"] += 1
                    bucket["night_first"] = bucket["night_first"] or ts.isoformat(sep=" ")
                    bucket["night_last"] = ts.isoformat(sep=" ")
                bucket["last_timestamp"] = ts.isoformat(sep=" ")
            if len(first_rows) < 5:
                first_rows.append({k: row.get(k) for k in headers})

        return {
            "file": path.name,
            "encoding": encoding,
            "delimiter": repr(delimiter),
            "headers": headers,
            "header_column_count": len(headers),
            "data_row_count": row_count,
            "blank_rows": blank_rows,
            "malformed_width_rows": malformed_width,
            "timestamp_errors": timestamp_errors,
            "numeric_errors": numeric_errors,
            "duplicate_timestamps": duplicate_timestamps,
            "out_of_order_timestamps": out_of_order,
            "ohlc_logic_errors": ohlc_errors,
            "negative_volume_rows": negative_volume,
            "first_timestamp": first_timestamp,
            "last_timestamp": last_timestamp,
            "trading_date_count": len(trading_dates),
            "daily_coverage_count_distribution": dict(sorted(Counter(str(v["total"]) for v in daily_coverage.values()).items(), key=lambda x: int(x[0]))),
            "daily_day_bar_count_distribution": dict(sorted(Counter(str(v["day"]) for v in daily_coverage.values()).items(), key=lambda x: int(x[0]))),
            "daily_night_bar_count_distribution": dict(sorted(Counter(str(v["night"]) for v in daily_coverage.values()).items(), key=lambda x: int(x[0]))),
            "daily_coverage_examples": list(daily_coverage.items())[:5],
            "daily_coverage_outliers": [
                {"trading_date": day, **values}
                for day, values in daily_coverage.items()
                if values["day"] not in (58, 60) or values["night"] not in (0, 168)
            ][:100],
            "interval_seconds_counts": dict(sorted(interval_counts.items(), key=lambda x: int(x[0]))),
            "interval_examples": {k: interval_examples[k] for k in sorted(interval_examples, key=int)},
            "interval_class_counts": dict(sorted(interval_classes.items())),
            "calendar_gap_class_counts": dict(sorted(calendar_gap_classes.items())),
            "calendar_gap_examples": calendar_gap_examples,
            "closure_calendar_dates": len(closures),
            "unexpected_interval_examples": unexpected_examples,
            "price_min": min_prices,
            "price_max": max_prices,
            "sample_first_rows": first_rows,
            "note": "Read-only audit. No records were filtered, repaired, or synthesized.",
        }


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("TMFR1_5min_2024-2025.csv")
    print(json.dumps(profile(target), ensure_ascii=False, indent=2))
