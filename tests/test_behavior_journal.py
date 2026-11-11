import json
from pathlib import Path
import pytest

from research_engine.behavior_journal import (
    append_journal_entry, create_journal_entry,
)


def test_journal_preserves_user_narrative_without_rule_interpretation(tmp_path):
    narrative = "我覺得回調沒有延續，所以先觀望；這只是當下描述。"
    entry = create_journal_entry(
        event_type="pre_trade",
        narrative=narrative,
        recorded_at="2026-11-11T10:00:00+08:00",
        market_timestamp="2026-11-11T09:58:00+08:00",
        context={"自述盤面": "高點附近來回", "信心": "不確定"},
    )
    path = tmp_path / "journal" / "behaviour.jsonl"
    result = append_journal_entry(journal_path=path, entry=entry)
    saved = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
    assert result["already_appended"] is False
    assert saved["narrative"] == narrative
    assert saved["context"] == entry["context"]
    assert "rules" not in saved


def test_append_is_idempotent_for_same_entry(tmp_path):
    path = tmp_path / "journal.jsonl"
    entry = create_journal_entry(event_type="observation", narrative="先記錄，不下結論。")
    append_journal_entry(journal_path=path, entry=entry)
    result = append_journal_entry(journal_path=path, entry=entry)
    assert result["already_appended"] is True
    assert len(path.read_text(encoding="utf-8").splitlines()) == 1


def test_duplicate_id_with_changed_content_is_rejected(tmp_path):
    path = tmp_path / "journal.jsonl"
    entry = create_journal_entry(event_type="exit", narrative="原始紀錄")
    append_journal_entry(journal_path=path, entry=entry)
    changed = {**entry, "narrative": "修改後"}
    with pytest.raises(ValueError, match="different content"):
        append_journal_entry(journal_path=path, entry=changed)


def test_invalid_event_and_timestamp_are_rejected():
    with pytest.raises(ValueError, match="event_type"):
        create_journal_entry(event_type="signal_rule", narrative="x")
    with pytest.raises(ValueError, match="ISO-8601"):
        create_journal_entry(event_type="observation", narrative="x", recorded_at="y")


def test_empty_narrative_is_rejected():
    with pytest.raises(ValueError, match="narrative"):
        create_journal_entry(event_type="observation", narrative="  ")
