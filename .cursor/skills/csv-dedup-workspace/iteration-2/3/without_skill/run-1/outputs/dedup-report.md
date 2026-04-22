# Deduplication Report

## Strategy

Rows were compared case-insensitively across all fields. The first occurrence of each unique row (by lowercased values) was retained; subsequent duplicates were removed. Headers were preserved exactly as provided.

## Summary

| Metric | Count |
|---|---|
| Original rows (excluding header) | 5 |
| Unique rows retained | 2 |
| Duplicate rows removed | 3 |

## Duplicates Removed

| Row # | Name | EMAIL | City | Duplicate of row |
|---|---|---|---|---|
| 3 | ALICE | alice@example.com | BOSTON | 1 |
| 4 | alice | ALICE@EXAMPLE.COM | boston | 1 |
| 5 | Bob | BOB@EXAMPLE.COM | Seattle | 2 |

## Output

See `dedup.csv` for the deduplicated result.
