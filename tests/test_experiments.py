import hashlib, json
from pathlib import Path
import pytest
from research_engine.experiments import create_experiment, record_experiment_result

def setup_registry(tmp_path):
    digest = "a" * 64
    registry = {"registry_version":"1.0.0","datasets":[{"dataset_id":"ds_1234567890abcdef","status":"accepted",
      "product_id":"TMFR1","timeframe":"5m","sha256":digest}]}
    path = tmp_path / "registry.json"; path.write_text(json.dumps(registry), encoding="utf-8")
    return path

def make_experiment(tmp_path):
    registry = setup_registry(tmp_path)
    return create_experiment(registry_path=registry, experiment_root=tmp_path / "experiments",
      dataset_id="ds_1234567890abcdef", strategy_id="fvg_open", strategy_version="0.1.0",
      parameters={"gap_min_points":5,"volume_filter":True},
      cost_model={"round_trip_cost_points":5.3,"slippage_points":1.0,"version":"v1"},
      execution_model={"model_id":"next_bar_open","version":"1.0"}, code_revision="abc123",
      hypothesis="Test opening FVG continuation")

def test_experiment_id_is_deterministic_and_spec_is_saved(tmp_path):
    first = make_experiment(tmp_path)
    second = make_experiment(tmp_path)
    assert first["experiment_id"] == second["experiment_id"]
    saved = json.loads(Path(first["path"]).read_text())
    assert saved["approval_status"] == "pending_human_approval"
    assert saved["run_status"] == "registered"
    assert saved["dataset_timeframe"] == "5m"

def test_different_cost_model_creates_different_experiment(tmp_path):
    first = make_experiment(tmp_path)
    registry = setup_registry(tmp_path)
    second = create_experiment(registry_path=registry, experiment_root=tmp_path / "experiments",
      dataset_id="ds_1234567890abcdef", strategy_id="fvg_open", strategy_version="0.1.0",
      parameters={"gap_min_points":5,"volume_filter":True},
      cost_model={"round_trip_cost_points":6.0,"slippage_points":1.0,"version":"v1"},
      execution_model={"model_id":"next_bar_open","version":"1.0"}, code_revision="abc123")
    assert first["experiment_id"] != second["experiment_id"]

def test_unknown_dataset_is_rejected(tmp_path):
    registry = setup_registry(tmp_path)
    with pytest.raises(ValueError, match="accepted registry"):
      create_experiment(registry_path=registry, experiment_root=tmp_path / "experiments",
        dataset_id="ds_unknown", strategy_id="s", strategy_version="1", parameters={},
        cost_model={"round_trip_cost_points":5.3,"slippage_points":0},
        execution_model={"model_id":"m","version":"1"}, code_revision="abc")

def test_formal_result_requires_human_approval(tmp_path):
    exp = make_experiment(tmp_path)
    with pytest.raises(ValueError, match="human approval"):
      record_experiment_result(experiment_root=tmp_path / "experiments",
        experiment_id=exp["experiment_id"], result={"net_points":10})

def test_result_is_immutable_after_approval(tmp_path):
    exp = make_experiment(tmp_path)
    path = Path(exp["path"]); spec = json.loads(path.read_text())
    spec["approval_status"] = "approved"
    path.write_text(json.dumps(spec), encoding="utf-8")
    args = {"experiment_root":tmp_path / "experiments","experiment_id":exp["experiment_id"]}
    record_experiment_result(**args, result={"net_points":10})
    with pytest.raises(FileExistsError, match="immutable"):
      record_experiment_result(**args, result={"net_points":11})