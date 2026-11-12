import pytest

from research_engine.costs import (
    TMFCostConfig, DynamicSlippageConfig,
    calculate_round_trip_cost_twd, dynamic_slippage_points,
)
from research_engine.models import Bar
from datetime import datetime, timedelta


def test_tmf_round_trip_tax_uses_both_execution_prices_and_multiplier():
    result = calculate_round_trip_cost_twd(22000, 22100, TMFCostConfig())
    assert result["commission_twd"] == 0
    assert result["futures_tax_twd"] == pytest.approx((22000 + 22100) * 10 * 0.00002)
    assert result["total_points"] == pytest.approx(result["total_twd"] / 10)


def test_broker_commission_is_configurable_per_side():
    result = calculate_round_trip_cost_twd(20000, 20010, TMFCostConfig(commission_per_side_twd=20))
    assert result["commission_twd"] == 40


def test_rejects_invalid_cost_config():
    with pytest.raises(ValueError):
        calculate_round_trip_cost_twd(20000, 20010, TMFCostConfig(commission_per_side_twd=-1))


def test_dynamic_slippage_uses_only_prior_volume_and_current_range():
    t = datetime(2025, 1, 1)
    bars = [
        Bar(t, 100, 102, 99, 101, 100),
        Bar(t + timedelta(minutes=5), 101, 103, 100, 102, 100),
        Bar(t + timedelta(minutes=10), 102, 112, 100, 110, 10),
    ]
    cfg = DynamicSlippageConfig(base_points=0.2, range_fraction=0.1,
                                low_volume_penalty_points=0.5, max_points=5)
    assert dynamic_slippage_points(bars, 2, cfg) == pytest.approx(1.9)


def test_dynamic_slippage_clamps_to_maximum():
    t = datetime(2025, 1, 1)
    bars = [Bar(t, 100, 200, 90, 150, 1)]
    cfg = DynamicSlippageConfig(base_points=1, range_fraction=1, max_points=2)
    assert dynamic_slippage_points(bars, 0, cfg) == 2
