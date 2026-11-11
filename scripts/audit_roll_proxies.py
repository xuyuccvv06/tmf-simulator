"""Describe expiry-window price behaviour without claiming roll identification.

The checked-in TMFR1 CSV has only a continuous product identifier. This script
reports observable session gaps around third-Wednesday expiry dates as proxies,
not verified roll spreads or contract-switch dates.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from pathlib import Path
from statistics import median


def third_wednesday(year: int, month: int) -> date:
    first = date(year, month, 1)
    return first + timedelta(days=(2 - first.weekday()) % 7 + 14)


def classify_session(ts: datetime) -> str:
    t = ts.time()
    if time(8, 45) <= t <= time(13, 44):
        return "DAY"
    if t >= time(15, 0) or t <= time(4, 59):
        return "NIGHT"
    raise ValueError(f"timestamp outside supported TMFR1 session windows: {ts}")


def load_sessions(path: Path) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"datetime", "trading_date", "open", "high", "low", "close", "volume"}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError(f"CSV must contain columns: {sorted(required)}")
        for row_no, row in enumerate(reader, start=2):
            ts = datetime.fromisoformat(row["datetime"])
            kind = classify_session(ts)
            grouped[(row["trading_date"], kind)].append({
                "timestamp": ts,
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": float(row["volume"]),
            })

    sessions = []
    for (trading_date, kind), bars in grouped.items():
        bars.sort(key=lambda b: b["timestamp"])
        sessions.append({
            "trading_date": trading_date,
            "kind": kind,
            "start": bars[0]["timestamp"],
            "end": bars[-1]["timestamp"],
            "open": bars[0]["open"],
            "high": max(b["high"] for b in bars),
            "low": min(b["low"] for b in bars),
            "close": bars[-1]["close"],
            "bar_count": len(bars),
            "volume": sum(b["volume"] for b in bars),
        })
    return sorted(sessions, key=lambda s: s["start"])


def build_report(path: Path) -> dict[str, object]:
    sessions = load_sessions(path)
    for index, session in enumerate(sessions):
        previous = sessions[index - 1] if index else None
        session["previous_session_close"] = previous["close"] if previous else None
        session["open_gap_points"] = (
            session["open"] - previous["close"] if previous else None
        )

    dates = sorted({
        date.fromisoformat(s["trading_date"])
        for s in sessions
    })
    expiry_dates = [
        third_wednesday(year, month)
        for year in (2024, 2025)
        for month in range(1, 13)
        if date(2024, 7, 29) <= third_wednesday(year, month) <= date(2025, 12, 31)
    ]

    windows = []
    for expiry in expiry_dates:
        window_sessions = [
            s for s in sessions
            if abs((date.fromisoformat(s["trading_date"]) - expiry).days) <= 2
        ]
        expiry_day = [
            s for s in window_sessions
            if s["trading_date"] == expiry.isoformat() and s["kind"] == "DAY"
        ]
        expiry_night = [
            s for s in window_sessions
            if s["trading_date"] == expiry.isoformat() and s["kind"] == "NIGHT"
        ]
        windows.append({
            "expiry_date": expiry.isoformat(),
            "expiry_day_session": expiry_day[0] if expiry_day else None,
            "expiry_trading_date_night_session": expiry_night[0] if expiry_night else None,
            "sessions_within_two_calendar_days": window_sessions,
            "warning": (
                "Observable continuous-series session behaviour only. "
                "Not proof of the actual contract switch, roll spread, or adjustment method."
            ),
        })

    gap_values = [
        abs(float(s["open_gap_points"]))
        for s in sessions
        if s["open_gap_points"] is not None
    ]
    return {
        "source_file": path.name,
        "session_count": len(sessions),
        "product_identity": "TMFR1 continuous series; individual expiry contract unavailable",
        "expiry_dates_count": len(expiry_dates),
        "all_session_abs_open_gap_median_points": median(gap_values) if gap_values else None,
        "expiry_windows": windows,
        "conclusion": (
            "No contract-level roll conclusion is possible from this file. "
            "The event windows are descriptive proxies only."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--output", type=Path, default=Path("tmfr1_expiry_window_audit.json"))
    args = parser.parse_args()
    report = build_report(args.csv_path)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps({
        "session_count": report["session_count"],
        "expiry_dates_count": report["expiry_dates_count"],
        "output": str(args.output),
        "conclusion": report["conclusion"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
