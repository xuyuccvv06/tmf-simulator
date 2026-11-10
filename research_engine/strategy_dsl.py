"""Allow-listed declarative strategy DSL. Never evaluates user-supplied code."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from math import isfinite
from typing import Any

ALLOWED_INDICATORS = {"open", "high", "low", "close", "volume", "sma", "volume_sma", "range_points", "body_points"}
ALLOWED_OPERATORS = {"gt", "gte", "lt", "lte", "eq"}

@dataclass(frozen=True)
class CompiledStrategy:
    strategy_id: str
    strategy_version: str
    timeframe: str
    side: str
    indicators: dict[str, dict]
    entry_all: tuple[dict, ...]
    entry_any: tuple[dict, ...]
    stop_points: float | None
    target_points: float | None

def _number(value: Any, name: str, *, minimum: float | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    if minimum is not None and value < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    return float(value)

def compile_strategy(spec: dict) -> CompiledStrategy:
    if not isinstance(spec, dict) or spec.get("dsl_version") != "1.0":
        raise ValueError("dsl_version must be 1.0")
    for key in ("strategy_id", "strategy_version"):
        if not isinstance(spec.get(key), str) or not spec[key].strip():
            raise ValueError(f"{key} is required")
    if spec.get("timeframe") not in {"1m", "5m"}:
        raise ValueError("timeframe must be 1m or 5m")
    if spec.get("side") not in {"long", "short", "both"}:
        raise ValueError("side must be long, short, or both")
    indicators = spec.get("indicators", {})
    if not isinstance(indicators, dict):
        raise ValueError("indicators must be an object")
    for name, definition in indicators.items():
        if not isinstance(name, str) or not name.isidentifier() or not isinstance(definition, dict):
            raise ValueError("indicator names and definitions must be valid objects")
        kind = definition.get("type")
        if kind not in ALLOWED_INDICATORS:
            raise ValueError(f"indicator type is not allowed: {kind}")
        if kind in {"sma", "volume_sma"}:
            period = definition.get("period")
            if isinstance(period, bool) or not isinstance(period, int) or not 1 <= period <= 500:
                raise ValueError(f"{name}.period must be an integer from 1 to 500")
    entry = spec.get("entry")
    if not isinstance(entry, dict):
        raise ValueError("entry must be an object")
    all_rules, any_rules = entry.get("all", []), entry.get("any", [])
    if not isinstance(all_rules, list) or not isinstance(any_rules, list) or (not all_rules and not any_rules):
        raise ValueError("entry requires non-empty all or any conditions")
    known = set(indicators)
    for field in ("open", "high", "low", "close", "volume", "range_points", "body_points"):
        known.add(field)
    for condition in all_rules + any_rules:
        if not isinstance(condition, dict) or condition.get("operator") not in ALLOWED_OPERATORS:
            raise ValueError("each condition requires an allowed operator")
        for operand in ("left", "right"):
            value = condition.get(operand)
            if isinstance(value, dict):
                if set(value) != {"indicator"} or value["indicator"] not in known:
                    raise ValueError("condition references an unknown indicator")
            else:
                _number(value, f"condition.{operand}")
    risk = spec.get("risk", {})
    if not isinstance(risk, dict):
        raise ValueError("risk must be an object")
    stop = risk.get("stop_points")
    target = risk.get("target_points")
    if stop is not None: stop = _number(stop, "stop_points", minimum=0.0000001)
    if target is not None: target = _number(target, "target_points", minimum=0.0000001)
    return CompiledStrategy(spec["strategy_id"], spec["strategy_version"], spec["timeframe"],
        spec["side"], indicators, tuple(all_rules), tuple(any_rules), stop, target)

def _series(bars, definition: dict) -> list[float]:
    kind = definition["type"]
    if kind in {"open", "high", "low", "close", "volume"}:
        return [float(getattr(bar, kind)) for bar in bars]
    if kind == "range_points": return [float(bar.high - bar.low) for bar in bars]
    if kind == "body_points": return [float(abs(bar.close - bar.open)) for bar in bars]
    source = "volume" if kind == "volume_sma" else definition.get("source", "close")
    if source not in {"open", "high", "low", "close", "volume", "range_points", "body_points"}:
        raise ValueError("SMA source is not allowed")
    values = _series(bars, {"type": source})
    period = definition["period"]
    result = [float("nan")] * len(values)
    rolling = 0.0
    for i, value in enumerate(values):
        rolling += value
        if i >= period: rolling -= values[i - period]
        if i >= period - 1: result[i] = rolling / period
    return result

def _resolve(value, i, bars, indicator_values):
    if isinstance(value, dict): return indicator_values[value["indicator"]][i]
    return float(value)

def _compare(left, operator, right):
    if not isfinite(left) or not isfinite(right): return False
    return {"gt": left > right, "gte": left >= right, "lt": left < right,
            "lte": left <= right, "eq": left == right}[operator]

def generate_orders(bars, strategy: CompiledStrategy):
    """Generate next-bar-open order intents from completed signal bars."""
    from .models import Order
    if not bars: return []
    indicator_values = {name: _series(bars, definition) for name, definition in strategy.indicators.items()}
    for field in ("open", "high", "low", "close", "volume", "range_points", "body_points"):
        indicator_values[field] = _series(bars, {"type": field})
    orders = []
    traded_dates: set[date] = set()
    sides = ("long", "short") if strategy.side == "both" else (strategy.side,)
    for i, bar in enumerate(bars[:-1]):
        def matches(condition):
            left = _resolve(condition["left"], i, bars, indicator_values)
            right = _resolve(condition["right"], i, bars, indicator_values)
            return _compare(left, condition["operator"], right)
        if strategy.entry_all and not all(matches(c) for c in strategy.entry_all): continue
        if strategy.entry_any and not any(matches(c) for c in strategy.entry_any): continue
        # One signal per side per trading date prevents accidental repeated entries in this V1 DSL.
        for side in sides:
            key = (bar.timestamp.date(), side)
            if key in traded_dates: continue
            orders.append(Order(bar.timestamp, side, strategy.stop_points, strategy.target_points))
            traded_dates.add(key)
    return orders

def run_dsl_strategy(bars, spec: dict, *, round_trip_cost_points: float, slippage_points: float = 0.0):
    """Compile DSL, generate intents, and call the deterministic baseline simulator."""
    from .simulator import simulate
    compiled = compile_strategy(spec)
    orders = generate_orders(bars, compiled)
    trades = simulate(bars, orders, round_trip_cost_points=round_trip_cost_points, slippage_points=slippage_points)
    return {"strategy_id": compiled.strategy_id, "strategy_version": compiled.strategy_version,
            "timeframe": compiled.timeframe, "signal_count": len(orders), "orders": orders, "trades": trades}