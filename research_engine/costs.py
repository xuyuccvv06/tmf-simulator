"""TMF transaction cost and execution-friction models.

Broker commission is user-configurable because the exchange states that the
fee charged to end customers is negotiated between broker and customer.
Exchange fee schedule values are reference costs paid by futures commission
merchants, not assumed retail commission.
"""
from dataclasses import dataclass
from math import isfinite

TMF_MULTIPLIER_TWD = 10.0
TMF_FUTURES_TAX_RATE = 0.00002


@dataclass(frozen=True)
class TMFCostConfig:
    commission_per_side_twd: float = 0.0
    futures_tax_rate: float = TMF_FUTURES_TAX_RATE
    multiplier_twd_per_point: float = TMF_MULTIPLIER_TWD
    contracts: int = 1

    def validate(self) -> None:
        for name, value in (
            ("commission_per_side_twd", self.commission_per_side_twd),
            ("futures_tax_rate", self.futures_tax_rate),
            ("multiplier_twd_per_point", self.multiplier_twd_per_point),
        ):
            if not isfinite(value) or value < 0:
                raise ValueError(f"{name} must be finite and non-negative")
        if self.contracts < 1:
            raise ValueError("contracts must be >= 1")


def calculate_round_trip_cost_twd(entry_price: float, exit_price: float, config: TMFCostConfig) -> dict:
    """Return broker commission, exchange tax, and total for entry + exit."""
    config.validate()
    if not all(isfinite(x) and x > 0 for x in (entry_price, exit_price)):
        raise ValueError("entry_price and exit_price must be finite and positive")
    multiplier = config.multiplier_twd_per_point * config.contracts
    commission = 2.0 * config.commission_per_side_twd * config.contracts
    tax = (entry_price + exit_price) * multiplier * config.futures_tax_rate
    total = commission + tax
    return {
        "commission_twd": commission,
        "futures_tax_twd": tax,
        "total_twd": total,
        "total_points": total / multiplier,
    }


@dataclass(frozen=True)
class DynamicSlippageConfig:
    """Transparent OHLCV proxy, not a measured order-book execution model.

    Slippage per side = base + range_fraction * bar_range + low-volume penalty.
    Volume reference is the median positive volume in the preceding window,
    excluding the current bar to avoid look-ahead.
    """
    base_points: float = 0.0
    range_fraction: float = 0.05
    low_volume_penalty_points: float = 0.5
    volume_threshold_ratio: float = 0.5
    min_points: float = 0.0
    max_points: float = 10.0
    lookback_bars: int = 20

    def validate(self) -> None:
        vals = (self.base_points, self.range_fraction, self.low_volume_penalty_points,
                self.volume_threshold_ratio, self.min_points, self.max_points)
        if not all(isfinite(x) and x >= 0 for x in vals):
            raise ValueError("slippage parameters must be finite and non-negative")
        if self.max_points < self.min_points or self.lookback_bars < 1:
            raise ValueError("invalid slippage bounds or lookback")


def dynamic_slippage_points(bars, index: int, config: DynamicSlippageConfig) -> float:
    """Estimate adverse slippage for one fill using only current/past OHLCV."""
    config.validate()
    if index < 0 or index >= len(bars):
        raise IndexError("bar index out of range")
    bar = bars[index]
    bar_range = max(0.0, float(bar.high) - float(bar.low))
    prior = [float(x.volume) for x in bars[max(0, index-config.lookback_bars):index]
             if isfinite(float(x.volume)) and float(x.volume) > 0]
    reference = sorted(prior)[len(prior)//2] if prior else 0.0
    current_volume = float(bar.volume) if isfinite(float(bar.volume)) else 0.0
    penalty = (config.low_volume_penalty_points
               if reference > 0 and current_volume < reference * config.volume_threshold_ratio else 0.0)
    raw = config.base_points + bar_range * config.range_fraction + penalty
    return min(config.max_points, max(config.min_points, raw))
