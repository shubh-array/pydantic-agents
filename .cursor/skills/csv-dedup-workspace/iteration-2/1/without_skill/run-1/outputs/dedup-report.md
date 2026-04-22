# Deduplication Report

## Summary

| Metric | Count |
|--------|-------|
| Original rows | 6 |
| Duplicate rows removed | 2 |
| Rows in output | 4 |

## Duplicates Removed

| # | Name | Age | City | Occurrences |
|---|------|-----|------|-------------|
| 1 | Alice | 30 | New York | 2 |
| 2 | Bob | 25 | Chicago | 2 |

## Output

Deduplicated data written to `dedup.csv`. The first occurrence of each unique row was retained; all subsequent duplicates were discarded.
