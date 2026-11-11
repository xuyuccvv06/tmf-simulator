from datetime import date, datetime

from research_engine.calendar_audit import classify_overnight_gap, load_closures


def test_loads_source_linked_closure_calendar():
    closures = load_closures("data/calendars/taifex_market_closures_2024_2025.csv")
    assert date(2024, 10, 3) in closures
    assert date(2024, 10, 10) in closures
    assert date(2024, 10, 31) in closures
    assert date(2025, 1, 23) in closures
    assert date(2025, 1, 24) in closures
    assert len(closures) == 23
    assert date(2025, 12, 25) in closures


def test_classifies_regular_weekend_gap():
    closures = {}
    result = classify_overnight_gap(
        datetime(2025, 1, 4, 4, 55),
        datetime(2025, 1, 6, 8, 45),
        closures,
    )
    assert result["classification"] == "explained_by_weekend"
    assert result["weekend_dates"] == ["2025-01-04", "2025-01-05"]


def test_classifies_official_closure_gap():
    closures = {
        date(2024, 10, 31): {
            "holiday": "Typhoon closure",
            "source_url": "https://example.com/official",
        }
    }
    result = classify_overnight_gap(
        datetime(2024, 10, 31, 4, 55),
        datetime(2024, 11, 1, 8, 45),
        closures,
    )
    assert result["classification"] == "explained_by_official_closure"
    assert result["official_closure_dates"] == ["2024-10-31"]


def test_does_not_assume_unlisted_weekday_is_a_holiday():
    result = classify_overnight_gap(
        datetime(2025, 1, 4, 4, 55),
        datetime(2025, 1, 7, 8, 45),
        {},
    )
    assert result["classification"] == "contains_unverified_weekday"
    assert result["unverified_weekdays"] == ["2025-01-06"]


def test_classifies_regular_same_date_overnight_break():
    result = classify_overnight_gap(
        datetime(2025, 1, 6, 4, 55),
        datetime(2025, 1, 6, 8, 45),
        {},
    )
    assert result["classification"] == "regular_overnight_break"
