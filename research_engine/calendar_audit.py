"""Classify long overnight-to-day gaps using the checked-in TAIFEX closure list.

The calendar is deliberately explicit and source-linked. Unlisted weekdays are
reported as unverified rather than silently assumed to be normal trading days.
"""
from __future__ import annotations

import csv
from datetime import date, datetime, timedelta
from pathlib import Path


def load_closures(path: str | Path) -> dict[date, dict[str, str]]:
    closures: dict[date, dict[str, str]] = {}
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            day = date.fromisoformat(row["date"])
            if day in closures:
                raise ValueError(f"duplicate closure date: {day}")
            if not row.get("source_url", "").startswith("https://"):
                raise ValueError(f"missing source URL for closure date: {day}")
            closures[day] = row
    return closures


def classify_overnight_gap(
    previous: datetime,
    current: datetime,
    closures: dict[date, dict[str, str]],
) -> dict[str, object]:
    if previous.time() != datetime.strptime("04:55", "%H:%M").time():
        return {"classification": "not_overnight_boundary", "intervening_dates": []}
    if current.time() != datetime.strptime("08:45", "%H:%M").time():
        return {"classification": "not_day_open_boundary", "intervening_dates": []}
    if current <= previous:
        raise ValueError("current timestamp must follow previous timestamp")

    days = []
    day = previous.date() + timedelta(days=1)
    while day < current.date():
        days.append(day)
        day += timedelta(days=1)

    closure_days = [d.isoformat() for d in days if d in closures]
    weekend_days = [d.isoformat() for d in days if d.weekday() >= 5]
    unverified_weekdays = [
        d.isoformat() for d in days
        if d.weekday() < 5 and d not in closures
    ]

    if unverified_weekdays:
        classification = "contains_unverified_weekday"
    elif closure_days:
        classification = "explained_by_official_closure"
    elif weekend_days:
        classification = "explained_by_weekend"
    else:
        classification = "unexplained_gap"

    return {
        "classification": classification,
        "intervening_dates": [d.isoformat() for d in days],
        "official_closure_dates": closure_days,
        "weekend_dates": weekend_days,
        "unverified_weekdays": unverified_weekdays,
    }
