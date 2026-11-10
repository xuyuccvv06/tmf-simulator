"""Small, explicit next-bar-open execution baseline; not an exchange matching engine."""
from .models import Bar, Order, Trade
from .validation import validate_bars

def simulate(bars: list[Bar], orders: list[Order], *, round_trip_cost_points: float = 5.3, slippage_points: float = 0.0) -> list[Trade]:
    errors = validate_bars(bars)
    if errors:
        raise ValueError("; ".join(errors))
    if round_trip_cost_points < 0 or slippage_points < 0:
        raise ValueError("cost and slippage must be non-negative")
    index = {bar.timestamp: i for i, bar in enumerate(bars)}
    trades: list[Trade] = []
    for order in orders:
        i = index.get(order.timestamp)
        if i is None or i + 1 >= len(bars):
            continue
        entry_bar = bars[i + 1]
        entry = entry_bar.open + slippage_points * (1 if order.side == "long" else -1)
        exit_i = None
        exit_price = None
        reason = "end_of_data"
        for j in range(i + 1, len(bars)):
            bar = bars[j]
            if order.stop_points is not None:
                stop = entry - order.stop_points if order.side == "long" else entry + order.stop_points
                touched = bar.low <= stop if order.side == "long" else bar.high >= stop
                if touched:
                    exit_i, exit_price, reason = j, stop, "stop"
                    break
            if order.target_points is not None:
                target = entry + order.target_points if order.side == "long" else entry - order.target_points
                touched = bar.high >= target if order.side == "long" else bar.low <= target
                if touched:
                    exit_i, exit_price, reason = j, target, "target"
                    break
        if exit_i is None:
            exit_i, exit_price = len(bars) - 1, bars[-1].close
        if order.side == "short":
            exit_price -= slippage_points
        else:
            exit_price += slippage_points
        gross = (exit_price - entry) * (1 if order.side == "long" else -1)
        cost = round_trip_cost_points
        trades.append(Trade(order.side, entry_bar.timestamp, bars[exit_i].timestamp, entry, exit_price, gross, cost, gross-cost, reason))
    return trades
