import pytest

from research_engine.trade_lifecycle import (
    append_trade_event, get_trade_timeline, list_trade_summaries, new_trade_id,
)


def add(path, trade_id, kind, narrative=None):
    return append_trade_event(
        journal_path=path, trade_id=trade_id, event_type=kind,
        narrative=narrative or kind, recorded_at="2026-11-11T10:00:00+08:00",
    )


def test_complete_lifecycle_keeps_events_linked_and_in_order(tmp_path):
    path = tmp_path / "journal.jsonl"
    trade_id = new_trade_id()
    for kind in ("pre_trade", "pre_trade", "entry", "management", "management", "exit", "post_trade"):
        add(path, trade_id, kind)
    timeline = get_trade_timeline(journal_path=path, trade_id=trade_id)
    assert [event["event_type"] for event in timeline] == [
        "pre_trade", "pre_trade", "entry", "management", "management", "exit", "post_trade"
    ]
    summary = list_trade_summaries(journal_path=path)[0]
    assert summary["lifecycle_complete"] is True
    assert summary["event_count"] == 7


def test_management_requires_entry_and_exit_requires_entry(tmp_path):
    path = tmp_path / "journal.jsonl"
    trade_id = new_trade_id()
    with pytest.raises(ValueError, match="prior entry"):
        add(path, trade_id, "management")
    with pytest.raises(ValueError, match="prior entry"):
        add(path, trade_id, "exit")


def test_entry_and_exit_cannot_be_duplicated(tmp_path):
    path = tmp_path / "journal.jsonl"
    trade_id = new_trade_id()
    add(path, trade_id, "entry")
    with pytest.raises(ValueError, match="only one entry"):
        add(path, trade_id, "entry")
    add(path, trade_id, "exit")
    with pytest.raises(ValueError, match="only one exit"):
        add(path, trade_id, "exit")


def test_post_trade_requires_exit_and_closes_lifecycle(tmp_path):
    path = tmp_path / "journal.jsonl"
    trade_id = new_trade_id()
    with pytest.raises(ValueError, match="prior exit"):
        add(path, trade_id, "post_trade")
    add(path, trade_id, "entry")
    add(path, trade_id, "exit")
    add(path, trade_id, "post_trade")
    with pytest.raises(ValueError, match="after exit"):
        add(path, trade_id, "management")


def test_incomplete_trade_is_reported_not_fabricated(tmp_path):
    path = tmp_path / "journal.jsonl"
    trade_id = new_trade_id()
    add(path, trade_id, "pre_trade")
    summary = list_trade_summaries(journal_path=path)[0]
    assert summary["has_entry"] is False
    assert summary["has_exit"] is False
    assert summary["lifecycle_complete"] is False


def test_observation_does_not_appear_in_trade_summary(tmp_path):
    path = tmp_path / "journal.jsonl"
    trade_id = new_trade_id()
    append_trade_event(
        journal_path=path, trade_id=trade_id, event_type="entry",
        narrative="手動進場", recorded_at="2026-11-11T10:00:00+08:00",
    )
    assert len(list_trade_summaries(journal_path=path)) == 1
