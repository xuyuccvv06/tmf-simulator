"""Append-only journal for capturing discretionary trading behaviour without predefining rules."""
from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

EVENT_TYPES = {"pre_trade", "entry", "management", "exit", "post_trade", "observation"}


def create_journal_entry(
    *,
    event_type: str,
    narrative: str,
    recorded_at: str | None = None,
    trade_id: str | None = None,
    market_timestamp: str | None = None,
    context: dict[str, Any] | None = None,
    attachments: list[str] | None = None,
) -> dict[str, Any]:
    """Create a faithful note; context remains user-described, not interpreted as rules."""
    if event_type not in EVENT_TYPES:
        raise ValueError("unsupported event_type")
    if not isinstance(narrative, str) or not narrative.strip():
        raise ValueError("narrative is required")
    timestamp = recorded_at or datetime.now().astimezone().isoformat()
    try:
        datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise ValueError("recorded_at must be an ISO-8601 timestamp") from exc
    if market_timestamp is not None:
        try:
            datetime.fromisoformat(market_timestamp.replace("Z", "+00:00"))
        except (TypeError, ValueError) as exc:
            raise ValueError("market_timestamp must be an ISO-8601 timestamp") from exc
    if context is not None and not isinstance(context, dict):
        raise ValueError("context must be an object")
    if attachments is not None and (
        not isinstance(attachments, list) or not all(isinstance(item, str) for item in attachments)
    ):
        raise ValueError("attachments must be a list of strings")
    entry = {
        "journal_version": "1.0.0",
        "entry_id": "jrn_" + uuid.uuid4().hex,
        "event_type": event_type,
        "recorded_at": timestamp,
        "market_timestamp": market_timestamp,
        "trade_id": trade_id,
        "narrative": narrative,
        "context": context or {},
        "attachments": attachments or [],
    }
    # Reject NaN/Infinity and non-JSON values before anything is persisted.
    json.dumps(entry, ensure_ascii=False, allow_nan=False)
    return entry


def append_journal_entry(*, journal_path: Path, entry: dict[str, Any]) -> dict[str, Any]:
    """Append one immutable JSONL event; never rewrites earlier observations."""
    if not isinstance(entry, dict) or not str(entry.get("entry_id", "")).startswith("jrn_"):
        raise ValueError("entry must be a journal entry with a valid entry_id")
    serialized = json.dumps(entry, ensure_ascii=False, sort_keys=True, allow_nan=False)
    journal_path.parent.mkdir(parents=True, exist_ok=True)
    if journal_path.exists():
        for line in journal_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                existing = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError("journal contains an invalid existing JSONL record") from exc
            if existing.get("entry_id") == entry["entry_id"]:
                if existing == entry:
                    return {"entry_id": entry["entry_id"], "path": str(journal_path), "already_appended": True}
                raise ValueError("entry_id already exists with different content")
    with journal_path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(serialized + "\n")
    return {"entry_id": entry["entry_id"], "path": str(journal_path), "already_appended": False}
