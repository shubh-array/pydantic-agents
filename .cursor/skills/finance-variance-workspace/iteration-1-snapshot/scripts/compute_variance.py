#!/usr/bin/env python3
"""
compute_variance.py — Budget vs. Actuals variance calculator.

Usage:
    python compute_variance.py <input_csv> [--output-dir <dir>]

Outputs:
    variance.csv   — original columns + variance + variance_pct
    summary.md     — totals and top-3 over-budget categories
"""

import argparse
import csv
import os
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Column name normalisation
# ---------------------------------------------------------------------------

CATEGORY_NAMES = {"category", "name", "dept", "department", "cost_centre"}
BUDGET_NAMES   = {"budget", "plan", "planned"}
ACTUAL_NAMES   = {"actual", "actuals", "spend", "spent"}


def _find_col(headers: list[str], accepted: set[str]) -> int | None:
    for i, h in enumerate(headers):
        if h.strip().lower() in accepted:
            return i
    return None


def _parse_number(raw: str) -> float:
    """Strip thousands separators and whitespace, then parse as float."""
    cleaned = raw.strip().replace(",", "")
    return float(cleaned)


def _fmt_pct(variance: float, budget: float) -> str:
    if budget == 0:
        return "N/A"
    pct = (variance / budget) * 100
    return f"{pct:.1f}%"


def _fmt_thousands(n: float) -> str:
    """Format a number with thousands separators, no decimals if whole."""
    if n == int(n):
        return f"{int(n):,}"
    return f"{n:,.2f}"


# ---------------------------------------------------------------------------
# Core processing
# ---------------------------------------------------------------------------

def process(input_path: str, output_dir: str) -> None:
    input_path = Path(input_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict] = []

    with open(input_path, encoding="utf-8-sig", newline="") as fh:
        reader = csv.reader(fh)
        raw_headers = next(reader)
        headers = [h.strip() for h in raw_headers]

        cat_i = _find_col(headers, CATEGORY_NAMES)
        bud_i = _find_col(headers, BUDGET_NAMES)
        act_i = _find_col(headers, ACTUAL_NAMES)

        # Positional fallback
        if cat_i is None: cat_i = 0
        if bud_i is None: bud_i = 1
        if act_i is None: act_i = 2

        for lineno, row in enumerate(reader, start=2):
            # Skip blank / all-whitespace lines
            if not any(cell.strip() for cell in row):
                continue
            try:
                category = row[cat_i].strip()
                budget   = _parse_number(row[bud_i])
                actual   = _parse_number(row[act_i])
            except (IndexError, ValueError) as exc:
                print(f"  Warning: skipping line {lineno}: {exc}", file=sys.stderr)
                continue
            variance = actual - budget
            rows.append({
                "category":     category,
                "budget":       budget,
                "actual":       actual,
                "variance":     variance,
                "variance_pct": _fmt_pct(variance, budget),
            })

    if not rows:
        sys.exit("No valid data rows found — check input file.")

    def _fmt_num(n: float) -> int | float:
        return int(n) if n == int(n) else round(n, 2)

    # ---- variance.csv -------------------------------------------------------
    variance_csv = output_dir / "variance.csv"
    with open(variance_csv, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=["category", "budget", "actual", "variance", "variance_pct"],
        )
        writer.writeheader()
        for r in rows:
            writer.writerow({
                "category":     r["category"],
                "budget":       _fmt_num(r["budget"]),
                "actual":       _fmt_num(r["actual"]),
                "variance":     _fmt_num(r["variance"]),
                "variance_pct": r["variance_pct"],
            })

    # ---- summary.md ---------------------------------------------------------
    total_budget   = sum(r["budget"]   for r in rows)
    total_actual   = sum(r["actual"]   for r in rows)
    total_variance = total_actual - total_budget
    total_pct      = _fmt_pct(total_variance, total_budget)

    over_budget = sorted(
        [r for r in rows if r["variance"] > 0],
        key=lambda r: r["variance"],
        reverse=True,
    )[:3]

    summary_md = output_dir / "summary.md"
    with open(summary_md, "w", encoding="utf-8") as fh:
        fh.write("# Budget vs. Actuals Summary\n\n")

        fh.write("## Totals\n")
        fh.write("| | Amount |\n|---|---|\n")
        fh.write(f"| Total Budget | {_fmt_thousands(total_budget)} |\n")
        fh.write(f"| Total Actual | {_fmt_thousands(total_actual)} |\n")
        fh.write(f"| Total Variance | {_fmt_thousands(total_variance)} |\n")
        fh.write(f"| Total Variance % | {total_pct} |\n\n")

        fh.write("## Top 3 Over-Budget Categories\n")
        if over_budget:
            fh.write("| Category | Budget | Actual | Variance | Variance % |\n")
            fh.write("|---|---|---|---|---|\n")
            for r in over_budget:
                fh.write(
                    f"| {r['category']} | {_fmt_thousands(r['budget'])} | "
                    f"{_fmt_thousands(r['actual'])} | {_fmt_thousands(r['variance'])} | "
                    f"{r['variance_pct']} |\n"
                )
        else:
            fh.write("_No categories were over budget._\n")

    print(f"Wrote: {variance_csv}")
    print(f"Wrote: {summary_md}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Budget vs. Actuals variance analysis")
    parser.add_argument("input_csv", help="Path to input CSV")
    parser.add_argument("--output-dir", default=".", help="Directory for output files")
    args = parser.parse_args()
    process(args.input_csv, args.output_dir)


if __name__ == "__main__":
    main()
