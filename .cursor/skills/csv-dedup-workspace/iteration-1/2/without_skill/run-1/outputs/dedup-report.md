# CSV Deduplication Report

## Summary

| Metric | Count |
|--------|-------|
| Original rows (excluding header) | 6 |
| Rows after deduplication | 3 |
| Duplicate rows removed | 3 |

## Processing Steps

1. **Whitespace trimming** — Leading and trailing spaces were stripped from every cell value before comparison.
2. **Duplicate detection** — Rows were considered duplicates if all field values matched after trimming.
3. **Retention policy** — The first occurrence of each unique row was kept.

## Duplicates Removed

| # | Original Row (as-is) | Reason |
|---|----------------------|--------|
| 1 | `Alice,30,New York` (row 4) | Duplicate of row 2 (`  Alice ,30, New York`) after trimming |
| 2 | `  Bob  ,25,Chicago` (row 5) | Duplicate of row 3 (`Bob,25,Chicago`) after trimming |
| 3 | `Carol,35,Boston` (row 7) | Duplicate of row 6 (`Carol,35,  Boston`) after trimming |

## Output

Clean, deduplicated data written to `dedup.csv` with 3 unique rows.
