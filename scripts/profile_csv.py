"""Profile the checked-in TMFR1 CSV without changing or repairing it.

This first-pass profiler deliberately avoids assuming a schema. It reports
encoding, delimiter, headers, row-width consistency, sample rows and basic
numeric-column ranges so the strict loader can be configured from evidence.
"""
from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from pathlib import Path


def open_text(path: Path):
    errors = []
    for encoding in ("utf-8-sig", "cp950", "big5"):
        try:
            handle = path.open("r", encoding=encoding, newline="")
            handle.read(4096)
            handle.seek(0)
            return handle, encoding
        except UnicodeDecodeError as exc:
            errors.append(f"{encoding}: {exc}")
    raise UnicodeError("Unable to decode CSV: " + " | ".join(errors))


def profile(path: Path) -> dict:
    handle, encoding = open_text(path)
    with handle:
        sample = handle.read(8192)
        handle.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\\t|")
            delimiter = dialect.delimiter
        except csv.Error:
            delimiter = ","
        reader = csv.reader(handle, delimiter=delimiter)
        try:
            headers = next(reader)
        except StopIteration:
            raise ValueError("CSV is empty")
        width_counts: Counter[int] = Counter()
        samples = []
        row_count = 0
        blank_rows = 0
        for row in reader:
            row_count += 1
            width_counts[len(row)] += 1
            if not row or all(not cell.strip() for cell in row):
                blank_rows += 1
            if len(samples) < 5:
                samples.append(row)
        return {
            "file": str(path),
            "encoding": encoding,
            "delimiter": repr(delimiter),
            "headers": headers,
            "header_column_count": len(headers),
            "data_row_count": row_count,
            "row_width_counts": dict(sorted(width_counts.items())),
            "blank_rows": blank_rows,
            "sample_first_rows": samples,
            "note": "Read-only profile; no rows were changed, filtered, or repaired.",
        }


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("TMFR1_5min_2024-2025.csv")
    print(json.dumps(profile(target), ensure_ascii=False, indent=2))
