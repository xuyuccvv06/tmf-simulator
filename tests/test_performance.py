from datetime import datetime, timedelta

import pytest

from research_engine.models import Trade
from research_engine.performance import summarize_trades


def make_trade(exit_minute, net, gross=None, cost=1):
    entry = datetime(2025, 1, 1) + timedelta(minutes=exit_minute - 5)
    exit_time = datetime(2025, 1, 1) + timedelta(minutes=exit_minute)
    gross = net + cost if gross is None else gross
    return Trade("long", entry, exit_time, 100, 100 + gross, gross, cost, net, "test")


def test_summary_win_rate_expectancy_and_costs():
    trades = [make_trade(5, 4), make_trade(10, -2), make_trade(15, 0)]
    result = summarize_trades(trades)
    assert result.trade_count == 3
    assert result.wins == 1
    assert result.losses == 1
    assert result.breakeven == 1
    assert result.win_rate == pytest.approx(1 / 3)
    assert result.net_points == 2
    assert result.expectancy_points == pytest.approx(2 / 3)
    assert result.total_cost_points == 3


def test_summary_drawdown_and_consecutive_losses():
    trades = [make_trade(5, 5), make_trade(10, -2), make_trade(15, -4), make_trade(20, 3)]
    result = summarize_trades(trades)
    assert result.max_drawdown_points == 6
    assert result.max_consecutive_losses == 2
    assert result.profit_factor == pytest.approx(8 / 6)


def test_empty_summary_is_defined():
    result = summarize_trades([])
    assert result.trade_count == 0
    assert result.win_rate == 0
    assert result.expectancy_points == 0
    assert result.profit_factor is None


def test_rejects_invalid_trade_values():
    trade = make_trade(5, float("nan"))
    with pytest.raises(ValueError):
        summarize_trades([trade])
