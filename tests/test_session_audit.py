from datetime import datetime

from research_engine.session_audit import classify_tmfr1_interval


def test_classifies_continuous_five_minute_bars():
    assert classify_tmfr1_interval(
        datetime(2025, 1, 2, 9, 0),
        datetime(2025, 1, 2, 9, 5),
    ) == "continuous_5m"


def test_classifies_regular_day_to_after_hours_break():
    assert classify_tmfr1_interval(
        datetime(2025, 1, 2, 13, 40),
        datetime(2025, 1, 2, 15, 0),
    ) == "day_to_after_hours"


def test_classifies_early_close_day_to_after_hours_break():
    assert classify_tmfr1_interval(
        datetime(2025, 1, 15, 13, 25),
        datetime(2025, 1, 15, 15, 0),
    ) == "day_to_after_hours"


def test_classifies_overnight_transition_across_holiday():
    assert classify_tmfr1_interval(
        datetime(2025, 1, 1, 4, 55),
        datetime(2025, 1, 2, 8, 45),
    ) == "after_hours_to_day"


def test_does_not_hide_unexpected_intraday_gap():
    assert classify_tmfr1_interval(
        datetime(2025, 1, 2, 9, 0),
        datetime(2025, 1, 2, 9, 15),
    ) == "unexpected_interval"
