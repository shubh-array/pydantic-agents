---
name: csv-dedup
description: >
  Deduplicate CSV files — removes duplicate rows and produces a clean output CSV
  plus a Markdown summary report. Use this skill whenever the user mentions:
  deduplicate CSV, remove duplicate rows, find duplicates in CSV, clean up CSV
  duplicates, "this CSV has dupes", merge duplicate records, CSV cleanup, eliminate
  repeated entries, or wants to filter/strip repeated rows from any tabular or
  spreadsheet data. Near-miss phrases like "my CSV has repeated lines", "get rid of
  double entries", "the same row appears twice", or "de-dupe my file" should also
  trigger this skill.
---

# csv-dedup

Given a CSV with duplicate rows, produce two files:

1. **`dedup.csv`** — the cleaned CSV, keeping the **first** occurrence of each
   duplicate and preserving original column order.
2. **`dedup-report.md`** — a Markdown report with totals and a table of every
   removed row.

## Deduplication rules

These rules exist to catch real-world messiness in CSV exports:

- **Trim whitespace for comparison only.** `"  Alice "` and `"Alice"` are
  duplicates, but the original cell value from the first occurrence is preserved
  verbatim in `dedup.csv`. Do not modify or normalize cell content in the output.
- **Case-insensitive** comparison on cell values — `"ALICE"` and `"alice"` are
  duplicates. Again, preserve the original casing in the output.
- **Headers** are preserved **exactly as-is** (do not normalize them).
- Keep the **first occurrence** of each group; remove all later duplicates.
- **Use `csv.DictReader`**, not naive comma-splitting. Fields like `"Smith, John"`
  (a value that contains a comma, quoted per RFC 4180) must be parsed as one cell.

## Steps

1. **Get the CSV data.** If the user pasted CSV content in their message, write it
   to `input.csv` in the working directory first. If they provided a file path,
   use it directly.

2. **Run the bundled script.** This skill ships with `scripts/dedup_csv.py`. Use
   it — it handles all edge cases (whitespace, case, quoted commas) correctly:

   ```bash
   python scripts/dedup_csv.py input.csv dedup.csv dedup-report.md
   ```

   The script path is relative to the skill directory. If the skill is at
   `.cursor/skills/csv-dedup/`, the full path is
   `.cursor/skills/csv-dedup/scripts/dedup_csv.py`. Adjust based on where you are.

   If you cannot locate the script, implement the same logic inline in Python
   (see the logic summary below).

3. **Verify outputs.** Confirm `dedup.csv` and `dedup-report.md` were written.
   Quick check: row count in `dedup.csv` should equal
   `(rows before) − (duplicates removed)`.

## Logic summary (if the script is unavailable)

```python
import csv
from pathlib import Path

with open("input.csv", newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    fieldnames = list(reader.fieldnames or [])
    rows = list(reader)

seen, kept, removed = set(), [], []
for i, row in enumerate(rows, start=2):
    # Trim + lowercase for comparison only; row dict stays untouched
    key = tuple(row[f].strip().lower() for f in fieldnames)
    if key in seen:
        removed.append((i, row))
    else:
        seen.add(key)
        kept.append(row)

with open("dedup.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=fieldnames)
    w.writeheader()
    w.writerows(kept)  # original cell values, unmodified
```

Then write `dedup-report.md` following the report template below.

## Report template

Always use this exact structure so downstream tools can parse it reliably:

```markdown
# CSV Dedup Report

| Metric | Value |
|--------|-------|
| Rows before | N |
| Rows after | M |
| Duplicates removed | K |

## Removed rows

| Row # | col1 | col2 | … |
|-------|------|------|---|
| 4     | val  | val  | … |
```

If no duplicates are found, replace the "Removed rows" section with:
`_No duplicates found — the CSV is already clean._`

## What the user should see in your final message

Briefly confirm: how many rows were in the input, how many remain in `dedup.csv`,
and how many duplicates were removed. Point them at the two output files. Keep it
short — the report itself has all the detail.
