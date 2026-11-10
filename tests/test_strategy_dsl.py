from datetime import datetime, timedelta
import pytest
from research_engine.models import Bar
from research_engine.strategy_dsl import compile_strategy, generate_orders, run_dsl_strategy

def bars(rows):
    start = datetime(2025, 1, 2, 9, 0)
    return [Bar(start + timedelta(minutes=5*i), *row) for i,row in enumerate(rows)]

def spec():
    return {"dsl_version":"1.0","strategy_id":"close_above_sma","strategy_version":"0.1.0",
      "timeframe":"5m","side":"long","indicators":{"trend":{"type":"sma","source":"close","period":2}},
      "entry":{"all":[{"left":{"indicator":"close"},"operator":"gt","right":{"indicator":"trend"}}],"any":[]},
      "risk":{"stop_points":10,"target_points":20}}

def test_compile_and_generate_signal_only_after_sma_warmup():
    data = bars([(100,101,99,100),(100,102,99,101),(101,104,100,103),(103,105,102,104)])
    compiled = compile_strategy(spec())
    orders = generate_orders(data, compiled)
    assert len(orders) == 1
    assert orders[0].timestamp == data[1].timestamp
    assert orders[0].side == "long"
    assert orders[0].stop_points == 10

def test_unknown_indicator_and_arbitrary_code_are_rejected():
    bad = spec(); bad["indicators"] = {"x":{"type":"__import__"}}
    with pytest.raises(ValueError, match="not allowed"): compile_strategy(bad)
    bad = spec(); bad["entry"]["all"][0]["left"] = {"expression":"__import__(os)"}
    with pytest.raises(ValueError, match="unknown indicator"): compile_strategy(bad)

def test_invalid_sma_period_is_rejected():
    bad = spec(); bad["indicators"]["trend"]["period"] = 0
    with pytest.raises(ValueError, match="period"): compile_strategy(bad)

def test_unknown_condition_operator_is_rejected():
    bad = spec(); bad["entry"]["all"][0]["operator"] = "eval"
    with pytest.raises(ValueError, match="operator"): compile_strategy(bad)

def test_run_dsl_strategy_uses_existing_simulator():
    data = bars([(100,101,99,100),(100,102,99,101),(101,104,100,103),(103,105,102,104)])
    result = run_dsl_strategy(data, spec(), round_trip_cost_points=5.3)
    assert result["signal_count"] == 1
    assert len(result["trades"]) == 1
def test_unknown_fields_are_rejected_at_every_level():
    bad = spec(); bad["python"] = "print('unsafe')"
    with pytest.raises(ValueError, match="top-level"):
        compile_strategy(bad)
    bad = spec(); bad["indicators"]["trend"]["expression"] = "__import__('os')"
    with pytest.raises(ValueError, match="unsupported indicator fields"):
        compile_strategy(bad)
    bad = spec(); bad["risk"]["trailing_stop"] = True
    with pytest.raises(ValueError, match="unsupported fields"):
        compile_strategy(bad)
