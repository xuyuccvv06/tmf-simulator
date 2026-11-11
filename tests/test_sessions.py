from datetime import datetime, time

import pytest

from research_engine.sessions import SessionWindow, classify_session, validate_session_windows


def test_classifies_day_and_overnight_windows():
    sessions = [
        SessionWindow("day", time(8, 45), time(13, 45)),
        SessionWindow("night", time(15, 0), time(5, 0)),
    ]
    assert classify_session(datetime(2025, 1, 2, 9, 0), sessions) == "day"
    assert classify_session(datetime(2025, 1, 2, 23, 30), sessions) == "night"
    assert classify_session(datetime(2025, 1, 2, 14, 0), sessions) is None


def test_session_end_is_exclusive():
    sessions = [SessionWindow("day", time(9, 0), time(13, 30))]
    assert classify_session(datetime(2025, 1, 2, 9, 0), sessions) == "day"
    assert classify_session(datetime(2025, 1, 2, 13, 30), sessions) is None


def test_rejects_overlapping_windows():
    sessions = [
        SessionWindow("a", time(9, 0), time(12, 0)),
        SessionWindow("b", time(11, 0), time(13, 0)),
    ]
    assert validate_session_windows(sessions)
    with pytest.raises(ValueError, match="overlapping"):
        classify_session(datetime(2025, 1, 2, 11, 30), sessions)


def test_rejects_invalid_session_window():
    with pytest.raises(ValueError, match="cannot be equal"):
        SessionWindow("bad", time(9, 0), time(9, 0))
