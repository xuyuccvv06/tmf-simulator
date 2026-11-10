"""Deterministic point-based performance statistics for closed trades."""
from dataclasses import dataclass
from math import isfinite

from .models import Trade


@dataclass(frozen=True)
class PerformanceSummary:
    trade_count: int
    wins: int
    losses: int
    breakeven: int
    win_rate: float
    gross_points: float
    total_cost_points: float
    net_points: float
    expectancy_points: float
    average_win_points: float
    average_loss_points: float
    profit_factor: float | None
    max_drawdown_points: float
    max_consecutive_losses: int


def summarize_trades(trades: list[Trade]) -> PerformanceSummary:
    """Summarize closed trades in chronological exit order.

    Drawdown is calculated from the cumulative net-points curve, starting at
    zero. Profit factor is None when there are no losing trades; no artificial
    infinity or fabricated denominator is returned.
    """
    for i, trade in enumerate(trades):
        if not isfinite(trade.net_points) or not isfinite(trade.gross_points) or not isfinite(trade.cost_points):
            raise ValueError(f"trade {i}: point values must be finite")
        if trade.cost_points < 0:
            raise ValueError(f"trade {i}: cost_points must be non-negative")
        if trade.exit_time < trade.entry_time:
            raise ValueError(f"trade {i}: exit_time precedes entry_time")

    ordered = sorted(trades, key=lambda trade: (trade.exit_time, trade.entry_time))
    count = len(ordered)
    wins_list = [t.net_points for t in ordered if t.net_points > 0]
    losses_list = [t.net_points for t in ordered if t.net_points < 0]
    breakeven = sum(t.net_points == 0 for t in ordered)
    net_values = [t.net_points for t in ordered]

    equity = 0.0
    peak = 0.0
    max_drawdown = 0.0
    current_losses = 0
    max_losses = 0
    for value in net_values:
        equity += value
        peak = max(peak, equity)
        max_drawdown = max(max_drawdown, peak - equity)
        if value < 0:
            current_losses += 1
            max_losses = max(max_losses, current_losses)
        else:
            current_losses = 0

    gross = sum(t.gross_points for t in ordered)
    costs = sum(t.cost_points for t in ordered)
    net = sum(net_values)
    gross_profit = sum(wins_list)
    gross_loss = abs(sum(losses_list))

    return PerformanceSummary(
        trade_count=count,
        wins=len(wins_list),
        losses=len(losses_list),
        breakeven=breakeven,
        win_rate=(len(wins_list) / count) if count else 0.0,
        gross_points=gross,
        total_cost_points=costs,
        net_points=net,
        expectancy_points=(net / count) if count else 0.0,
        average_win_points=(gross_profit / len(wins_list)) if wins_list else 0.0,
        average_loss_points=(sum(losses_list) / len(losses_list)) if losses_list else 0.0,
        profit_factor=(gross_profit / gross_loss) if gross_loss else None,
        max_drawdown_points=max_drawdown,
        max_consecutive_losses=max_losses,
    )
