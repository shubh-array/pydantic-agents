---
name: finance-variance
description: >
  Produces budget-vs-actual variance analysis from a CSV. Use whenever the user
  mentions budget vs actuals, variance analysis, monthly spend review, comparing
  budget to actual, over/under budget, or wants to analyse any CSV with budget and
  actual spend columns — even without the word "variance". Near-miss phrases like
  "see how we did against plan", "monthly finance review", "check our spend", or
  "did we stay in budget" should also trigger this skill.
---

# finance-variance

Given a CSV of monthly budget versus actuals, produce two files in the current working directory:

1. **`variance.csv`** — original columns plus `variance` and `variance_pct`.
2. **`summary.md`** — totals row and the top 3 over-budget categories.

## Triggering

Use this skill whenever someone provides (or asks you to process) a CSV where columns represent a category or cost-centre alongside a budget amount and an actual amount. You don't need an explicit "run variance analysis" request — if the context clearly involves comparing planned spend to real spend, this skill applies.

## How to execute

Write the Python script below to `compute_variance.py` in the current working directory, save the input CSV as `budget.csv` (or use whatever name is provided), then run:

```bash
python compute_variance.py budget.csv
```

If the prompt embeds CSV data (e.g. as a code block or inline text), write it to `budget.csv` first, then run the script. If a CSV file path is already given, pass that path instead.

## Python script (write to `compute_variance.py`)

```python
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
    def _fmt_num(n):
        return int(n) if n == int(n) else round(n, 2)
    # variance.csv
    with open(output_dir / "variance.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["category","budget","actual","variance","variance_pct"])
        w.writeheader()
        for r in rows:
            w.writerow({"category": r["category"], "budget": _fmt_num(r["budget"]),
                        "actual": _fmt_num(r["actual"]), "variance": _fmt_num(r["variance"]),
                        "variance_pct": r["variance_pct"]})
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
```

## Output specification

### variance.csv

```
category,budget,actual,variance,variance_pct
Marketing,10000,12500,2500,25.0%
Engineering,50000,48000,-2000,-4.0%
```

- `variance` = `actual − budget` (positive = over budget, negative = under budget).
- `variance_pct` = one decimal place with `%` sign, no space (e.g. `"25.0%"`, `"-4.0%"`). Zero budget → `"N/A"`.
- Numeric columns in variance.csv are plain numbers (no thousands separators, no currency symbols).

### summary.md

```markdown
# Budget vs. Actuals Summary

## Totals
| | Amount |
|---|---|
| Total Budget | 60,000 |
| Total Actual | 60,500 |
| Total Variance | 500 |
| Total Variance % | 0.8% |

## Top 3 Over-Budget Categories
| Category | Budget | Actual | Variance | Variance % |
|---|---|---|---|---|
| Marketing | 10,000 | 12,500 | 2,500 | 25.0% |
```

- "Over budget" = `variance > 0` (actual exceeded budget). Rank by variance descending.
- If fewer than 3 categories are over budget, list only those.
- Format numbers in summary.md with thousands separators for readability (no currency symbol).

## Edge cases

The script handles these automatically — you do not need to preprocess the CSV:

- **Quoted categories with commas** — e.g., `"Travel, domestic"`. Python's `csv.reader` handles RFC-4180 quoting.
- **Thousands separators in numeric cells** — e.g., `"1,250.00"`. The `_parse_num` function strips commas before `float()`.
- **Trailing blank lines** — silently skipped (any row where every cell is whitespace-only is ignored).
- **BOM / UTF-8 encoding** — file is opened with `encoding="utf-8-sig"`.
- **Case-insensitive column matching** — `Budget`, `BUDGET`, and `budget` all resolve correctly.
