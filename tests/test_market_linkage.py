from datetime import datetime, timedelta, timezone
import pytest

from research_engine.market_linkage import create_market_reference, resolve_market_reference
from research_engine.models import Bar


SHA = "a" * 64
BASE = datetime(2026, 11, 11, 9, 0, tzinfo=timezone(timedelta(hours=8)))
BARS = [
    Bar(BASE + timedelta(minutes=5*i), 100+i, 102+i, 99+i, 101+i, 10)
    for i in range(4)
]


def make_reference(start=BASE, end=BASE + timedelta(minutes=10)):
    return create_market_reference(
        dataset_id="ds_tmfr1_5m_v1", dataset_sha256=SHA, timeframe="5m",
        start_timestamp=start.isoformat(), end_timestamp=end.isoformat(),
    )


def test_reference_resolves_exact_market_bars():
    ref = make_reference()
    result = resolve_market_reference(
        reference=ref, bars=BARS, dataset_id="ds_tmfr1_5m_v1", dataset_sha256=SHA
    )
    assert [bar.timestamp for bar in result] == [b.timestamp for b in BARS[:3]]


def test_dataset_identity_mismatch_is_rejected():
    with pytest.raises(ValueError, match="dataset_sha256"):
        resolve_market_reference(
            reference=make_reference(), bars=BARS,
            dataset_id="ds_tmfr1_5m_v1", dataset_sha256="b" * 64,
        )


def test_non_exact_boundary_is_not_rounded_to_nearest_bar():
    with pytest.raises(LookupError, match="exact dataset bar timestamps"):
        resolve_market_reference(
            reference=make_reference(start=BASE + timedelta(minutes=1)),
            bars=BARS, dataset_id="ds_tmfr1_5m_v1", dataset_sha256=SHA,
        )


def test_empty_window_fails_explicitly():
    ref = make_reference(
        start=BASE + timedelta(minutes=20), end=BASE + timedelta(minutes=25)
    )
    with pytest.raises(LookupError, match="no bars"):
        resolve_market_reference(
            reference=ref, bars=BARS, dataset_id="ds_tmfr1_5m_v1", dataset_sha256=SHA
        )


def test_invalid_or_reversed_reference_is_rejected():
    with pytest.raises(ValueError, match="SHA-256"):
        create_market_reference(
            dataset_id="ds", dataset_sha256="bad", timeframe="5m",
            start_timestamp=BASE.isoformat(), end_timestamp=BASE.isoformat(),
        )
    with pytest.raises(ValueError, match="end_timestamp"):
        make_reference(start=BASE + timedelta(minutes=10), end=BASE)
