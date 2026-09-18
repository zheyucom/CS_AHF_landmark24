#!/usr/bin/env python3
"""Merge four browser-exported 112 CSV batches and verify completeness."""

from __future__ import annotations

import csv
import sys
from pathlib import Path


EXPECTED_ROWS = 7828
KEYS = ("stay_id", "note_id")


def read(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    if len(sys.argv) != 6:
        raise SystemExit(
            "Usage: merge_landmark12_radiology_batches.py batch0.csv batch2000.csv "
            "batch4000.csv batch6000.csv output.csv"
        )
    inputs = [Path(x) for x in sys.argv[1:5]]
    output = Path(sys.argv[5])
    rows: list[dict[str, str]] = []
    headers: list[str] | None = None
    for path in inputs:
        batch = read(path)
        if headers is None:
            headers = list(batch[0]) if batch else None
        if batch and list(batch[0]) != headers:
            raise SystemExit(f"Header mismatch: {path}")
        rows.extend(batch)
        print(f"{path.name}: {len(batch)} rows")
    if headers is None:
        raise SystemExit("No rows found")
    keys = [(row.get(KEYS[0], ""), row.get(KEYS[1], "")) for row in rows]
    if len(rows) != EXPECTED_ROWS:
        raise SystemExit(f"Expected {EXPECTED_ROWS} rows, got {len(rows)}")
    if len(set(keys)) != len(keys):
        raise SystemExit(f"Duplicate report keys: {len(keys) - len(set(keys))}")
    rows.sort(key=lambda row: (int(row["stay_id"]), row["charttime"], row["note_id"]))
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Complete merge: {len(rows)} rows -> {output}")


if __name__ == "__main__":
    main()
