# Deduplication Report

## Summary

| Metric | Count |
|---|---|
| Original rows | 6 |
| Duplicate rows removed | 2 |
| Rows in output | 4 |

## Duplicate Rows Removed

| # | Name | Age | City |
|---|---|---|---|
| 1 | Alice | 30 | New York |
| 2 | Bob | 25 | Chicago |

## Output

Deduplicated data written to `dedup.csv`. The first occurrence of each row was kept; all subsequent duplicates were discarded.
