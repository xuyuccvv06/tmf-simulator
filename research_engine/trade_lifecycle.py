"""Administrative lifecycle helpers for grouping a trader's own journal events.

The lifecycle validates record linkage and event order only. It does not
interpret chart structure, define entry criteria, or judge trade quality.
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from .behavior_journal import append_journal_entry, create_journal_entry

TRADE_EVENTS = {"pre_trade", "entry", "management", "exit", "post_trade"}


def new_trade_id() -> str:
    """Return an opaque identifier; it carries no market or strategy meaning."""
    return "trd_" + uuid.uuid4().hex


def _read_events(journal_path: Path) -> list[dict[str, Any]]:
    if not journal_path.exists():
        return []
    events = []
    for line_number, line in enumerate(journal_path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid journal JSON on line {line_number}") from exc
        events.append(event)
    return events


def _validate_trade_sequence(events: list[dict[str, Any]], trade_id: str, event_type: str) -> None:
    existing = [event for event in events if event.get("trade_id") == trade_id]
    types = [event.get("event_type") for event in existing]
    if any(kind not in TRADE_EVENTS for kind in types):
        raise ValueError("trade_id is already used by an unsupported event type")
    if event_type not in TRADE_EVENTS:
        raise ValueError("event_type must belong to a trade lifecycle")
    if event_type == "pre_trade":
        if "entry" in types:
            raise ValueError("pre_trade cannot be appended after entry")
        return
    if event_type == "entry":
        if "entry" in types:
            raise ValueError("a trade can have only one entry event")
        if "exit" in types or "post_trade" in types:
            raise ValueError("entry cannot be appended after exit or post_trade")
        return
    if event_type == "management":
        if "entry" not in types:
            raise ValueError("management requires a prior entry event")
        if "exit" in types or "post_trade" in types:
            raise ValueError("management cannot be appended after exit")
        return
    if event_type == "exit":
        if "entry" not in types:
            raise ValueError("exit requires a prior entry event")
        if "exit" in types or "post_trade" in types:
            raise ValueError("a trade can have only one exit event")
        return
    if event_type == "post_trade":
        if "exit" not in types:
            raise ValueError("post_trade requires a prior exit event")
        if "post_trade" in types:
            raise ValueError("a trade can have only one post_trade event")


def append_trade_event(
    *,
    journal_path: Path,
    trade_id: str,
    event_type: str,
    narrative: str,
    recorded_at: str | None = None,
    market_timestamp: str | None = None,
    context: dict[str, Any] | None = None,
    attachments: list[str] | None = None,
) -> dict[str, Any]:
    """Validate administrative event order, then append an immutable event."""
    if not isinstance(trade_id, str) or not trade_id.startswith("trd_"):
        raise ValueError("trade_id must be created by new_trade_id")
    events = _read_events(journal_path)
    _validate_trade_sequence(events, trade_id, event_type)
    entry = create_journal_entry(
        event_type=event_type,
        narrative=narrative,
        recorded_at=recorded_at,
        trade_id=trade_id,
        market_timestamp=market_timestamp,
        context=context,
        attachments=attachments,
    )
    return append_journal_entry(journal_path=journal_path, entry=entry)


def get_trade_timeline(*, journal_path: Path, trade_id: str) -> list[dict[str, Any]]:
    """Return all events for one trade in append order, without rewriting them."""
    if not isinstance(trade_id, str) or not trade_id.startswith("trd_"):
        raise ValueError("invalid trade_id")
    return [event for event in _read_events(journal_path) if event.get("trade_id") == trade_id]


def list_trade_summaries(*, journal_path: Path) -> list[dict[str, Any]]:
    """Build neutral summaries; missing stages are reported, never inferred."""
    grouped: dict[str, list[dict[str, Any]]] = {}
    for event in _read_events(journal_path):
        trade_id = event.get("trade_id")
        if trade_id:
            grouped.setdefault(trade_id, []).append(event)
    summaries = []
    for trade_id, events in grouped.items():
        types = [event.get("event_type") for event in events]
        summaries.append({
            "trade_id": trade_id,
            "event_count": len(events),
            "event_types": types,
            "first_recorded_at": events[0].get("recorded_at"),
            "last_recorded_at": events[-1].get("recorded_at"),
            "has_entry": "entry" in types,
            "has_exit": "exit" in types,
            "has_post_trade": "post_trade" in types,
            "lifecycle_complete": all(kind in types for kind in ("entry", "exit", "post_trade")),
        })
    return summaries
