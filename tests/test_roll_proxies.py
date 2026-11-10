from datetime import date
from pathlib import Path

from scripts.audit_roll_proxies import build_report, classify_session, third_wednesday


def test_third_wednesday_dates():
    assert third_wednesday(2025, 1) == date(2025, 1, 15)
    assert third_wednesday(2025, 12) == date(2025, 12, 17)


def test_session_classifier():
    from datetime import datetime
    assert classify_session(datetime(2025, 1, 2, 8, 45)) == "DAY"
    assert classify_session(datetime(2025, 1, 1, 15, 0)) == "NIGHT"
    assert classify_session(datetime(2025, 1, 2, 4, 55)) == "NIGHT"


def test_report_explicitly_disclaims_contract_level_roll(tmp_path: Path):
    source = tmp_path / "tiny.csv"
    source.write_text(
        "datetime,trading_date,open,high,low,close,volume\n"
        "2025-01-02 08:45:00,2025-01-02,22000,22010,21990,22005,10\n"
        "2025-01-02 08:50:00,2025-01-02,22005,22015,22000,22010,12\n",
        encoding="utf-8",
    )
    report = build_report(source)
    assert report["product_identity"].startswith("TMFR1 continuous")
    assert report["expiry_dates_count"] == 17
    assert "No contract-level roll conclusion" in report["conclusion"]
