#!/usr/bin/env python3
"""
Deduplicate a CSV file.

Usage:
    python dedup_csv.py <input.csv> [output.csv] [report.md]

Defaults:
    output.csv  -> dedup.csv
    report.md   -> dedup-report.md

Rules:
- Cell values are stripped of leading/trailing whitespace before comparing.
- Comparison is case-insensitive on all cell values.
- Headers are preserved exactly as-is.
- Column order is preserved.
- The first occurrence of each duplicate group is kept.
"""

import csv
import sys
from pathlib import Path


def dedup_csv(
    input_path: str,
    out_csv: str = "dedup.csv",
    out_report: str = "dedup-report.md",
) -> None:
    with open(input_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    seen: set[tuple[str, ...]] = set()
    kept: list[dict] = []
    removed: list[tuple[int, dict]] = []

    for i, row in enumerate(rows, start=2):  # row 1 is the header
        key = tuple(row[f].strip().lower() for f in fieldnames)
        if key in seen:
            removed.append((i, row))
        else:
            seen.add(key)
            kept.append(row)

    # Write dedup.csv
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(kept)

    # Build report
    total_before = len(rows)
    total_after = len(kept)
    n_removed = len(removed)

    sep = "|" + "|".join("---" for _ in fieldnames) + "|"
    header_row = "| " + " | ".join(fieldnames) + " |"

    lines = [
        "# CSV Dedup Report",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Rows before | {total_before} |",
        f"| Rows after | {total_after} |",
        f"| Duplicates removed | {n_removed} |",
        "",
    ]

    if removed:
        lines += [
            "## Removed rows",
            "",
            "| Row # | " + " | ".join(fieldnames) + " |",
            "|-------" + "|---" * len(fieldnames) + "|",
        ]
        for row_num, row in removed:
            vals = " | ".join(str(row[f]) for f in fieldnames)
            lines.append(f"| {row_num} | {vals} |")
    else:
        lines.append("_No duplicates found — the CSV is already clean._")

    Path(out_report).write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(
        f"Done. {total_before} rows in → {total_after} rows out. "
        f"{n_removed} duplicate(s) removed."
    )


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python dedup_csv.py <input.csv> [output.csv] [report.md]")
        sys.exit(1)
    inp = sys.argv[1]
    outp_csv = sys.argv[2] if len(sys.argv) > 2 else "dedup.csv"
    outp_md = sys.argv[3] if len(sys.argv) > 3 else "dedup-report.md"
    dedup_csv(inp, outp_csv, outp_md)
