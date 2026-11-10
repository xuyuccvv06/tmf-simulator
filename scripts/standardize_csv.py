"""Strict, non-destructive conversion to the TMF canonical OHLCV CSV schema."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime
from pathlib import Path

ALIASES = {
    "timestamp": ("datetime", "timestamp", "date_time", "時間", "日期時間"),
    "trading_date": ("trading_date", "交易日", "交易日期"),
    "open": ("open", "開盤", "開盤價"),
    "high": ("high", "最高", "最高價"),
    "low": ("low", "最低", "最低價"),
    "close": ("close", "收盤", "收盤價"),
    "volume": ("volume", "成交量", "vol"),
    "product_id": ("product_id", "symbol", "商品代碼"),
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_headers(headers: list[str]) -> dict[str, str]:
    normalized = {name.strip().lower(): name for name in headers if name}
    result = {}
    for field, aliases in ALIASES.items():
        match = next((normalized[a] for a in aliases if a in normalized), None)
        if match:
            result[field] = match
    required = ("timestamp", "trading_date", "open", "high", "low", "close", "volume")
    missing = [field for field in required if field not in result]
    if missing:
        raise ValueError(f"missing required source columns: {missing}")
    return result


def standardize(source: Path, output: Path, manifest_path: Path, timeframe: str) -> dict:
    if timeframe not in {"1m", "5m"}:
        raise ValueError("timeframe must be explicitly set to 1m or 5m")
    if source.resolve() == output.resolve():
        raise ValueError("output must not overwrite the source file")

    source_hash = sha256_file(source)
    row_count = 0
    first_timestamp = last_timestamp = None
    products = set()
    previous = None

    with source.open("r", encoding="utf-8-sig", newline="") as input_handle:
        reader = csv.DictReader(input_handle)
        if not reader.fieldnames:
            raise ValueError("source CSV has no header")
        columns = resolve_headers(reader.fieldnames)
        with output.open("w", encoding="utf-8", newline="") as output_handle:
            fields = ["timestamp", "trading_date", "product_id", "timeframe",
                      "open", "high", "low", "close", "volume"]
            writer = csv.DictWriter(output_handle, fieldnames=fields)
            writer.writeheader()
            for line, row in enumerate(reader, start=2):
                if None in row or any(row.get(columns[k]) is None for k in
                                      ("timestamp", "trading_date", "open", "high", "low", "close", "volume")):
                    raise ValueError(f"row {line}: malformed or missing required value")
                raw_ts = row[columns["timestamp"]].strip()
                ts = datetime.fromisoformat(raw_ts.replace("Z", "+00:00"))
                if ts.tzinfo is not None:
                    raise ValueError(f"row {line}: expected source-local naive timestamp; aware values need explicit timezone conversion")
                if previous is not None and ts <= previous:
                    raise ValueError(f"row {line}: timestamps must be strictly increasing")
                previous = ts
                values = {k: float(row[columns[k]].replace(",", "").strip())
                          for k in ("open", "high", "low", "close", "volume")}
                o, h, l, c, v = (values[k] for k in ("open", "high", "low", "close", "volume"))
                if min(o, h, l, c) <= 0 or l > min(o, c) or h < max(o, c) or v < 0:
                    raise ValueError(f"row {line}: invalid OHLCV values")
                product = row[columns["product_id"]].strip() if "product_id" in columns else "TMFR1"
                if not product:
                    raise ValueError(f"row {line}: blank product_id")
                products.add(product)
                timestamp = ts.isoformat(sep=" ")
                first_timestamp = first_timestamp or timestamp
                last_timestamp = timestamp
                writer.writerow({
                    "timestamp": timestamp,
                    "trading_date": row[columns["trading_date"]].strip(),
                    "product_id": product,
                    "timeframe": timeframe,
                    **{k: format(v, ".10g") for k, v in values.items()},
                })
                row_count += 1

    if len(products) != 1:
        raise ValueError(f"source contains multiple product identifiers: {sorted(products)}")
    manifest = {
        "schema_version": "1.0.0",
        "source_file": source.name,
        "source_sha256": source_hash,
        "output_file": output.name,
        "output_sha256": sha256_file(output),
        "row_count": row_count,
        "first_timestamp": first_timestamp,
        "last_timestamp": last_timestamp,
        "product_id": next(iter(products)),
        "timeframe": timeframe,
        "timezone": "Asia/Taipei",
        "timestamp_interpretation": "Source naive timestamps retained as Taiwan local wall time; no clock shift",
        "continuous_contract": next(iter(products)) == "TMFR1",
        "individual_contract_identity": False if next(iter(products)) == "TMFR1" else None,
        "transformations": ["column mapping", "canonical column ordering", "numeric serialization"],
        "row_filtering": False,
        "gap_filling": False,
        "synthetic_rows": 0,
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--timeframe", choices=("1m", "5m"), required=True)
    args = parser.parse_args()
    result = standardize(args.source, args.output, args.manifest, args.timeframe)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
