# CSV Deduplication Report

## Summary

| Metric | Count |
|---|---|
| Original rows (excluding header) | 6 |
| Rows after deduplication | 3 |
| Duplicates removed | 3 |

## Processing Steps

1. **Trimmed whitespace** from all cell values (leading/trailing spaces stripped).
2. **Identified duplicate rows** after normalization.
3. **Retained first occurrence** of each unique row.

## Duplicates Removed

| Row # | Name | Age | City | Duplicate of |
|---|---|---|---|---|
| 3 | `Alice` | `30` | `New York` | Row 1 (`  Alice `, `30`, ` New York`) |
| 4 | `  Bob  ` | `25` | `Chicago` | Row 2 (`Bob`, `25`, `Chicago`) |
| 6 | `Carol` | `35` | `Boston` | Row 5 (`Carol`, `35`, `  Boston`) |

## Final Deduplicated Data

| Name | Age | City |
|---|---|---|
| Alice | 30 | New York |
| Bob | 25 | Chicago |
| Carol | 35 | Boston |
