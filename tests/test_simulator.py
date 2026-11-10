from datetime import datetime, timedelta
from research_engine.models import Bar, Order
from research_engine.simulator import simulate

def test_next_bar_open_and_cost():
    t = datetime(2025, 1, 1)
    bars = [Bar(t,100,101,99,100), Bar(t+timedelta(minutes=5),101,103,100,102), Bar(t+timedelta(minutes=10),102,104,101,103)]
    trades = simulate(bars, [Order(t, "long")], round_trip_cost_points=5.3)
    assert len(trades) == 1
    assert trades[0].entry_price == 101
    assert trades[0].net_points == -3.3
