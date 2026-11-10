"""Immutable experiment specifications and separately stored run results."""
from __future__ import annotations
import hashlib, json, math
from pathlib import Path

def _canonical_json(value: dict) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValueError("experiment specification must be finite JSON data") from exc

def _write_new(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_text(encoding="utf-8") == content:
            return
        raise FileExistsError("immutable record already exists with different content: %s" % path)
    path.write_text(content, encoding="utf-8")

def create_experiment(*, registry_path: Path, experiment_root: Path, dataset_id: str,
                      strategy_id: str, strategy_version: str, parameters: dict,
                      cost_model: dict, execution_model: dict, code_revision: str,
                      hypothesis: str = "") -> dict:
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    matches = [item for item in registry.get("datasets", []) if item.get("dataset_id") == dataset_id]
    if len(matches) != 1 or matches[0].get("status") != "accepted":
        raise ValueError("dataset_id must resolve to exactly one accepted registry record")
    dataset = matches[0]
    if not strategy_id.strip() or not strategy_version.strip() or not code_revision.strip():
        raise ValueError("strategy_id, strategy_version, and code_revision are required")
    if not isinstance(parameters, dict) or not isinstance(cost_model, dict) or not isinstance(execution_model, dict):
        raise ValueError("parameters, cost_model, and execution_model must be objects")
    for key in ("round_trip_cost_points", "slippage_points"):
        value = cost_model.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            raise ValueError("cost_model.%s must be finite and non-negative" % key)
    if not execution_model.get("model_id") or not execution_model.get("version"):
        raise ValueError("execution_model requires model_id and version")
    spec = {
        "spec_version": "1.0.0", "dataset_id": dataset_id, "dataset_sha256": dataset["sha256"],
        "dataset_product_id": dataset["product_id"], "dataset_timeframe": dataset["timeframe"],
        "strategy_id": strategy_id, "strategy_version": strategy_version, "parameters": parameters,
        "cost_model": cost_model, "execution_model": execution_model, "code_revision": code_revision,
        "hypothesis": hypothesis, "approval_status": "pending_human_approval", "run_status": "registered",
    }
    spec_json = _canonical_json(spec)
    experiment_id = "exp_" + hashlib.sha256(spec_json.encode("utf-8")).hexdigest()[:20]
    record = {"experiment_id": experiment_id, **spec}
    content = json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n"
    path = experiment_root / (experiment_id + ".json")
    _write_new(path, content)
    return {"experiment_id": experiment_id, "path": str(path), "record": record}

def record_experiment_result(*, experiment_root: Path, experiment_id: str, result: dict) -> dict:
    if not experiment_id.startswith("exp_") or len(experiment_id) != 24:
        raise ValueError("invalid experiment_id")
    spec_path = experiment_root / (experiment_id + ".json")
    if not spec_path.exists():
        raise FileNotFoundError("experiment specification not found")
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    if spec.get("approval_status") != "approved":
        raise ValueError("human approval is required before attaching a formal result")
    result_json = _canonical_json(result)
    result_hash = hashlib.sha256(result_json.encode("utf-8")).hexdigest()
    result_record = {"experiment_id": experiment_id, "result_sha256": result_hash, "result": result}
    path = experiment_root / (experiment_id + ".result.json")
    _write_new(path, json.dumps(result_record, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n")
    return {"experiment_id": experiment_id, "result_sha256": result_hash, "path": str(path)}