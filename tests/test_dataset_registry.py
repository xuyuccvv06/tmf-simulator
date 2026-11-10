import csv, json
from pathlib import Path
import pytest
from scripts.dataset_registry import register_dataset, validate_dataset

def make_files(tmp_path):
    csv_path = tmp_path / "standard.csv"
    rows = [
      {"timestamp":"2025-01-02 08:45:00","trading_date":"2025-01-02","product_id":"TMFR1","timeframe":"5m","open":"22000","high":"22010","low":"21990","close":"22005","volume":"10"},
      {"timestamp":"2025-01-02 08:50:00","trading_date":"2025-01-02","product_id":"TMFR1","timeframe":"5m","open":"22005","high":"22015","low":"22000","close":"22010","volume":"12"},
    ]
    fields = list(rows[0])
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerows(rows)
    import hashlib
    digest = hashlib.sha256(csv_path.read_bytes()).hexdigest()
    manifest = {"schema_version":"1.0.0","output_file":"standard.csv","output_sha256":digest,
      "row_count":2,"first_timestamp":rows[0]["timestamp"],"last_timestamp":rows[1]["timestamp"],
      "product_id":"TMFR1","timeframe":"5m","row_filtering":False,"gap_filling":False,
      "synthetic_rows":0,"source_sha256":"abc","timezone":"Asia/Taipei",
      "continuous_contract":True,"individual_contract_identity":False}
    manifest_path = tmp_path / "manifest.json"; manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return csv_path, manifest_path

def test_register_dataset_creates_content_addressed_record(tmp_path):
    csv_path, manifest_path = make_files(tmp_path)
    registry_path = tmp_path / "registry.json"
    result = register_dataset(csv_path, manifest_path, registry_path)
    assert result["record"]["dataset_id"].startswith("ds_")
    assert result["record"]["status"] == "accepted"
    assert result["already_registered"] is False
    assert len(json.loads(registry_path.read_text())["datasets"]) == 1

def test_registration_is_idempotent(tmp_path):
    csv_path, manifest_path = make_files(tmp_path); registry_path = tmp_path / "registry.json"
    register_dataset(csv_path, manifest_path, registry_path)
    result = register_dataset(csv_path, manifest_path, registry_path)
    assert result["already_registered"] is True
    assert len(json.loads(registry_path.read_text())["datasets"]) == 1

def test_hash_mismatch_is_rejected(tmp_path):
    csv_path, manifest_path = make_files(tmp_path)
    csv_path.write_text(csv_path.read_text() + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="SHA-256"): validate_dataset(csv_path, manifest_path)

def test_non_destructive_manifest_is_required(tmp_path):
    csv_path, manifest_path = make_files(tmp_path)
    manifest = json.loads(manifest_path.read_text()); manifest["gap_filling"] = True
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="non-destructive"): validate_dataset(csv_path, manifest_path)
