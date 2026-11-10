import csv
import json
from pathlib import Path

import pytest

from scripts.standardize_csv import standardize


def test_standardize_preserves_rows_and_writes_provenance(tmp_path: Path):
    source = tmp_path / "source.csv"
    source.write_text(
        "datetime,trading_date,open,high,low,close,volume\n"
        "2025-01-02 08:45:00,2025-01-02,22000,22010,21990,22005,10\n"
        "2025-01-02 08:50:00,2025-01-02,22005,22015,22000,22010,12\n",
        encoding="utf-8",
    )
    output = tmp_path / "standard.csv"
    manifest_path = tmp_path / "manifest.json"
    manifest = standardize(source, output, manifest_path, "5m")

    with output.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 2
    assert rows[0]["product_id"] == "TMFR1"
    assert rows[0]["timeframe"] == "5m"
    assert manifest["row_filtering"] is False
    assert manifest["gap_filling"] is False
    assert manifest["synthetic_rows"] == 0
    assert json.loads(manifest_path.read_text())["source_sha256"] == manifest["source_sha256"]


def test_standardize_rejects_non_monotonic_timestamps(tmp_path: Path):
    source = tmp_path / "source.csv"
    source.write_text(
        "datetime,trading_date,open,high,low,close,volume\n"
        "2025-01-02 08:50:00,2025-01-02,22000,22010,21990,22005,10\n"
        "2025-01-02 08:45:00,2025-01-02,22005,22015,22000,22010,12\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="strictly increasing"):
        standardize(source, tmp_path / "out.csv", tmp_path / "manifest.json", "5m")


def test_standardize_rejects_overwriting_source(tmp_path: Path):
    source = tmp_path / "source.csv"
    source.write_text("datetime,trading_date,open,high,low,close,volume\n", encoding="utf-8")
    with pytest.raises(ValueError, match="must not overwrite"):
        standardize(source, source, tmp_path / "manifest.json", "5m")


def test_standardize_requires_explicit_timeframe(tmp_path: Path):
    source = tmp_path / "source.csv"
    source.write_text("datetime,trading_date,open,high,low,close,volume\n", encoding="utf-8")
    with pytest.raises(ValueError, match="timeframe"):
        standardize(source, tmp_path / "out.csv", tmp_path / "manifest.json", "15m")
