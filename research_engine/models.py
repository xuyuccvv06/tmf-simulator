"""Typed domain models for reproducible TMF research."""
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

Side = Literal["long", "short"]

@dataclass(frozen=True)
class Bar:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0

@dataclass(frozen=True)
class Order:
    timestamp: datetime
    side: Side
    stop_points: float | None = None
    target_points: float | None = None

@dataclass(frozen=True)
class Trade:
    side: Side
    entry_time: datetime
    exit_time: datetime
    entry_price: float
    exit_price: float
    gross_points: float
    cost_points: float
    net_points: float
    exit_reason: str
