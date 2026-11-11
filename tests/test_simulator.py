from datetime import datetime, timedelta

import pytest

from research_engine.models import Bar, Order
from research_engine.simulator import simulate


def make_bars(rows):
    t = datetime(2025, 1, 1)
    return [Bar(t + timedelta(minutes=5 * i), *row) for i, row in enumerate(rows)]


def test_next_bar_open_and_cost():
    bars = make_bars([(100, 101, 99, 100), (101, 103, 100, 102), (102, 104, 101, 103)])
    trades = simulate(bars, [Order(bars[0].timestamp, "long")], round_trip_cost_points=5.3)
    assert len(trades) == 1
    assert trades[0].entry_price == 101
    assert trades[0].net_points == pytest.approx(-3.3)


def test_slippage_is_adverse_on_both_sides():
    bars = make_bars([(100, 101, 99, 100), (100, 104, 99, 103), (103, 106, 102, 105)])
    trade = simulate(
        bars,
        [Order(bars[0].timestamp, "long", target_points=4)],
        round_trip_cost_points=0,
        slippage_points=1,
    )[0]
    assert trade.entry_price == 101
    assert trade.exit_price == 104  # target 105 less one point exit slippage
    assert trade.gross_points == 3


def test_stop_gap_fills_at_worse_open():
    bars = make_bars([(100, 101, 99, 100), (100, 102, 99, 101), (90, 92, 89, 91)])
    trade = simulate(
        bars,
        [Order(bars[0].timestamp, "long", stop_points=5)],
        round_trip_cost_points=0,
        slippage_points=1,
    )[0]
    assert trade.exit_reason == "stop"
    assert trade.exit_price == 89  # gap open 90, then adverse slippage
    assert trade.gross_points == -12


def test_stop_wins_when_stop_and_target_touch_same_bar():
    bars = make_bars([(100, 101, 99, 100), (100, 106, 94, 100)])
    trade = simulate(
        bars,
        [Order(bars[0].timestamp, "long", stop_points=5, target_points=5)],
        round_trip_cost_points=0,
    )[0]
    assert trade.exit_reason == "stop"
    assert trade.exit_price == 95


def test_rejects_invalid_risk_and_slippage():
    bars = make_bars([(100, 101, 99, 100), (100, 101, 99, 100)])
    with pytest.raises(ValueError):
        simulate(bars, [Order(bars[0].timestamp, "long", stop_points=0)])
    with pytest.raises(ValueError):
        simulate(bars, [Order(bars[0].timestamp, "long")], slippage_points=-1)
