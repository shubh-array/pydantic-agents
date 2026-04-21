#!/usr/bin/env python3
import argparse, csv, sys
from pathlib import Path

CATEGORY_NAMES = {"category","name","dept","department","cost_centre"}
BUDGET_NAMES   = {"budget","plan","planned"}
ACTUAL_NAMES   = {"actual","actuals","spend","spent"}

def _find_col(headers, accepted):
    for i, h in enumerate(headers):
        if h.strip().lower() in accepted:
            return i
    return None

def _parse_num(raw):
    return float(raw.strip().replace(",", ""))

def _fmt_pct(variance, budget):
    if budget == 0:
        return "N/A"
    return f"{(variance / budget) * 100:.1f}%"

def _fmt_thousands(n):
    return f"{int(n):,}" if n == int(n) else f"{n:,.2f}"

def process(input_path, output_dir):
    input_path, output_dir = Path(input_path), Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    with open(input_path, encoding="utf-8-sig", newline="") as fh:
        reader = csv.reader(fh)
        headers = [h.strip() for h in next(reader)]
        cat_i = _find_col(headers, CATEGORY_NAMES) or 0
        bud_i = _find_col(headers, BUDGET_NAMES)   or 1
        act_i = _find_col(headers, ACTUAL_NAMES)   or 2
        for lineno, row in enumerate(reader, 2):
            if not any(c.strip() for c in row):
                continue
            try:
                cat = row[cat_i].strip()
                bud = _parse_num(row[bud_i])
                act = _parse_num(row[act_i])
            except (IndexError, ValueError) as e:
                print(f"  Warning line {lineno}: {e}", file=sys.stderr)
                continue
            var = act - bud
            rows.append({"category": cat, "budget": bud, "actual": act,
                         "variance": var, "variance_pct": _fmt_pct(var, bud)})
    if not rows:
        sys.exit("No valid data rows found.")
    # variance.csv
    with open(output_dir / "variance.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["category","budget","actual","variance","variance_pct"])
        w.writeheader()
        w.writerows(rows)
    # summary.md
    tb = sum(r["budget"] for r in rows)
    ta = sum(r["actual"] for r in rows)
    tv = ta - tb
    over = sorted([r for r in rows if r["variance"] > 0],
                  key=lambda r: r["variance"], reverse=True)[:3]
    with open(output_dir / "summary.md", "w", encoding="utf-8") as fh:
        fh.write("# Budget vs. Actuals Summary\n\n")
        fh.write("## Totals\n| | Amount |\n|---|---|\n")
        fh.write(f"| Total Budget | {_fmt_thousands(tb)} |\n")
        fh.write(f"| Total Actual | {_fmt_thousands(ta)} |\n")
        fh.write(f"| Total Variance | {_fmt_thousands(tv)} |\n")
        fh.write(f"| Total Variance % | {_fmt_pct(tv, tb)} |\n\n")
        fh.write("## Top 3 Over-Budget Categories\n")
        if over:
            fh.write("| Category | Budget | Actual | Variance | Variance % |\n|---|---|---|---|---|\n")
            for r in over:
                fh.write(f"| {r['category']} | {_fmt_thousands(r['budget'])} | "
                         f"{_fmt_thousands(r['actual'])} | {_fmt_thousands(r['variance'])} | "
                         f"{r['variance_pct']} |\n")
        else:
            fh.write("_No categories were over budget._\n")
    print(f"Done. Wrote variance.csv and summary.md to {output_dir}")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("input_csv")
    p.add_argument("--output-dir", default=".")
    args = p.parse_args()
    process(args.input_csv, args.output_dir)
