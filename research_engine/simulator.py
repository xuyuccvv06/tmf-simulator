"""Conservative next-bar-open baseline simulator.

This is an independent-trade research primitive, not a portfolio or exchange
matching engine. If stop and target are both touched in one OHLC bar, stop wins.
Stop gaps fill at the bar open (then adverse exit slippage); target fills at its
limit price (then configured adverse exit slippage).
"""
from math import isfinite

from .models import Bar, Order, Trade
from .costs import TMFCostConfig, DynamicSlippageConfig, calculate_round_trip_cost_twd, dynamic_slippage_points
from .validation import validate_bars


def _validate_orders(orders: list[Order]) -> None:
    for i, order in enumerate(orders):
        if order.side not in ("long", "short"):
            raise ValueError(f"order {i}: side must be 'long' or 'short'")
        for name, value in (("stop_points", order.stop_points), ("target_points", order.target_points)):
            if value is not None and (not isfinite(value) or value <= 0):
                raise ValueError(f"order {i}: {name} must be a finite positive number")


def simulate(
    bars: list[Bar],
    orders: list[Order],
    *,
    round_trip_cost_points: float = 5.3,
    slippage_points: float = 0.0,
    tmf_cost_config: TMFCostConfig | None = None,
    dynamic_slippage_config: DynamicSlippageConfig | None = None,
) -> list[Trade]:
    """Simulate each order independently, entering at the next bar's open.

    Slippage is charged adversely on both entry and exit. Round-trip fees/tax
    are deducted once from gross points. Orders without a following bar, or
    whose timestamp is absent from the bar series, are skipped.
    """
    errors = validate_bars(bars)
    if errors:
        raise ValueError("; ".join(errors))
    _validate_orders(orders)
    if not isfinite(round_trip_cost_points) or round_trip_cost_points < 0:
        raise ValueError("round_trip_cost_points must be finite and non-negative")
    if not isfinite(slippage_points) or slippage_points < 0:
        raise ValueError("slippage_points must be finite and non-negative")
    if tmf_cost_config is not None:
        tmf_cost_config.validate()
    if dynamic_slippage_config is not None:
        dynamic_slippage_config.validate()
    if not bars:
        return []

    index = {bar.timestamp: i for i, bar in enumerate(bars)}
    trades: list[Trade] = []
    for order in orders:
        i = index.get(order.timestamp)
        if i is None or i + 1 >= len(bars):
            continue

        direction = 1 if order.side == "long" else -1
        entry_bar = bars[i + 1]
        entry_slippage = (dynamic_slippage_points(bars, i + 1, dynamic_slippage_config)
                          if dynamic_slippage_config is not None else slippage_points)
        entry = entry_bar.open + direction * entry_slippage
        exit_i = len(bars) - 1
        exit_price = bars[-1].close
        reason = "end_of_data"

        for j in range(i + 1, len(bars)):
            bar = bars[j]
            stop = None
            target = None
            if order.stop_points is not None:
                stop = entry - direction * order.stop_points
            if order.target_points is not None:
                target = entry + direction * order.target_points

            # Stop has priority when both levels are touched in the same bar.
            if stop is not None:
                stop_touched = bar.low <= stop if direction == 1 else bar.high >= stop
                if stop_touched:
                    # A gap through the stop is filled at the worse opening price.
                    exit_i = j
                    exit_price = min(bar.open, stop) if direction == 1 else max(bar.open, stop)
                    reason = "stop"
                    break

            if target is not None:
                target_touched = bar.high >= target if direction == 1 else bar.low <= target
                if target_touched:
                    exit_i = j
                    exit_price = target
                    reason = "target"
                    break

        # Exit slippage is always adverse to the position.
        exit_slippage = (dynamic_slippage_points(bars, exit_i, dynamic_slippage_config)
                         if dynamic_slippage_config is not None else slippage_points)
        exit_price -= direction * exit_slippage
        gross = (exit_price - entry) * direction
        if tmf_cost_config is not None:
            cost = calculate_round_trip_cost_twd(entry, exit_price, tmf_cost_config)["total_points"]
        else:
            cost = round_trip_cost_points
        trades.append(
            Trade(
                order.side,
                entry_bar.timestamp,
                bars[exit_i].timestamp,
                entry,
                exit_price,
                gross,
                cost,
                gross - cost,
                reason,
            )
        )
    return trades
