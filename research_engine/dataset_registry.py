"""Append-only dataset registry with content-addressed identity and revalidation."""
from __future__ import annotations
import csv
import hashlib
import json
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass

CANONICAL_COLUMNS = ["timestamp", "trading_date", "product_id", "timeframe", "open", "high", "low", "close", "volume"]
ALLOWED_TIMEFRAMES = {"1m", "5m"}

def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

@dataclass(frozen=True)
class DatasetRecord:
    dataset_id: str
    status: str
    product_id: str
    timeframe: str
    row_count: int
    sha256: str

def validate_dataset(csv_path: Path, manifest_path: Path) -> dict:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("timeframe") not in ALLOWED_TIMEFRAMES:
        raise ValueError("unsupported or missing timeframe")
    if manifest.get("row_filtering") is not False or manifest.get("gap_filling") is not False or manifest.get("synthetic_rows") != 0:
        raise ValueError("manifest does not certify non-destructive conversion")
    if manifest.get("output_file") != csv_path.name:
        raise ValueError("manifest output_file does not match CSV filename")
    actual_hash = sha256_file(csv_path)
    if actual_hash != manifest.get("output_sha256"):
        raise ValueError("standardized CSV SHA-256 does not match manifest")
    count = 0
    first = last = None
    products = set()
    timeframes = set()
    previous = None
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != CANONICAL_COLUMNS:
            raise ValueError("canonical CSV header or column order mismatch")
        for line, row in enumerate(reader, start=2):
            if None in row or any(row.get(k) is None or not row[k].strip() for k in CANONICAL_COLUMNS):
                raise ValueError("row %d: missing or malformed canonical value" % line)
            ts = datetime.fromisoformat(row["timestamp"])
            if ts.tzinfo is not None:
                raise ValueError("row %d: expected naive Asia/Taipei wall time" % line)
            if previous is not None and ts <= previous:
                raise ValueError("row %d: timestamps are not strictly increasing" % line)
            previous = ts
            for key in ("open", "high", "low", "close", "volume"):
                value = float(row[key])
                if not __import__("math").isfinite(value):
                    raise ValueError("row %d: non-finite %s" % (line, key))
            o, h, l, c, v = (float(row[k]) for k in ("open", "high", "low", "close", "volume"))
            if min(o, h, l, c) <= 0 or l > min(o, c) or h < max(o, c) or v < 0:
                raise ValueError("row %d: invalid OHLCV" % line)
            products.add(row["product_id"])
            timeframes.add(row["timeframe"])
            first = first or row["timestamp"]
            last = row["timestamp"]
            count += 1
    if count == 0:
        raise ValueError("dataset is empty")
    if len(products) != 1 or len(timeframes) != 1:
        raise ValueError("dataset mixes product identifiers or timeframes")
    product = next(iter(products))
    timeframe = next(iter(timeframes))
    if product != manifest.get("product_id") or timeframe != manifest.get("timeframe"):
        raise ValueError("CSV product/timeframe does not match manifest")
    if count != manifest.get("row_count") or first != manifest.get("first_timestamp") or last != manifest.get("last_timestamp"):
        raise ValueError("CSV row count or time range does not match manifest")
    dataset_id = "ds_" + actual_hash[:16]
    return {"dataset_id": dataset_id, "status": "accepted", "product_id": product, "timeframe": timeframe,
            "row_count": count, "sha256": actual_hash, "source_sha256": manifest.get("source_sha256"),
            "first_timestamp": first, "last_timestamp": last, "schema_version": manifest.get("schema_version"),
            "timezone": manifest.get("timezone"), "continuous_contract": manifest.get("continuous_contract"),
            "individual_contract_identity": manifest.get("individual_contract_identity"),
            "csv_file": csv_path.name, "manifest_file": manifest_path.name}

def register_dataset(csv_path: Path, manifest_path: Path, registry_path: Path) -> dict:
    record = validate_dataset(csv_path, manifest_path)
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    if registry_path.exists():
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
    else:
        registry = {"registry_version": "1.0.0", "datasets": []}
    if registry.get("registry_version") != "1.0.0" or not isinstance(registry.get("datasets"), list):
        raise ValueError("invalid registry structure or version")
    for existing in registry["datasets"]:
        if existing.get("dataset_id") == record["dataset_id"]:
            if existing != record:
                raise ValueError("dataset ID collision with different metadata; registry is append-only")
            return {"registry": str(registry_path), "record": record, "already_registered": True}
        if existing.get("sha256") == record["sha256"]:
            raise ValueError("same content already registered under a different dataset ID")
    registry["datasets"].append(record)
    registry_path.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"registry": str(registry_path), "record": record, "already_registered": False}
